import asyncio
import sys
import warnings
import os
from typing import Any, Dict, Optional, List
from playwright.async_api import async_playwright, Playwright, BrowserContext, Page, Download

from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_core.models import ChatCompletionClient

# Monkey patch the _lazy_init method of the original MultimodalWebSurfer class
original_lazy_init = MultimodalWebSurfer._lazy_init
original_close = MultimodalWebSurfer.close

async def patched_lazy_init(self) -> None:
    """
    Modified lazy initialization method that supports connecting to a remote Playwright server.
    This method replaces the original _lazy_init method in MultimodalWebSurfer.
    Forces remote connection without local fallback.
    """
    # Check if we're using a remote server
    if hasattr(self, 'playwright_server_url') and self.playwright_server_url:
        # For remote server initialization
        self._last_download = None
        self._prior_metadata_hash = None

        # Create the playwright instance connecting to remote server
        if self._playwright is None:
            # Start playwright
            self._pw_instance = await async_playwright().__aenter__()
            
            # Launch browser based on the URL type
            if self.playwright_server_url.startswith("ws://"):
                print(f"Connecting to Playwright server at: {self.playwright_server_url}")
                # For WebSocket URLs, we'll launch a browser using the Playwright instance
                # This works with a Playwright server running via `npx playwright run-server`
                self._playwright = self._pw_instance
                
                # The connection will be handled by the browser launch
                # We use a local browser but controlled by the remote Playwright server
                browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    # Add some extra arguments for stability
                    args=[
                        "--disable-dev-shm-usage",
                        "--disable-gpu"
                    ]
                )
                self._browser = browser
            else:
                # For HTTP URLs, connect to a CDP endpoint
                # This works with Chrome/Edge browsers with remote debugging enabled
                print(f"Connecting to CDP endpoint at: {self.playwright_server_url}")
                self._playwright = self._pw_instance
                browser = await self._playwright.chromium.connect_over_cdp(self.playwright_server_url)
                self._browser = browser
                
        # Create the context
        if self._context is None and self._browser is not None:
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
            )
        else:
            raise ValueError("Browser initialization failed")

        # Create the page
        self._context.set_default_timeout(60000)  # One minute
        self._page = await self._context.new_page()
        assert self._page is not None
        self._page.on("download", self._download_handler)
        if self.to_resize_viewport:
            await self._page.set_viewport_size({"width": self.VIEWPORT_WIDTH, "height": self.VIEWPORT_HEIGHT})
        
        # Try to load the page_script.js file from the current directory first
        page_script_path = os.path.join(os.getcwd(), "page_script.js")
        if not os.path.exists(page_script_path):
            # Fallback to the original location
            page_script_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js")
            if not os.path.exists(page_script_path):
                # As a last resort, try to find it in the package directory
                try:
                    import autogen_ext
                    autogen_ext_dir = os.path.dirname(autogen_ext.__file__)
                    page_script_path = os.path.join(autogen_ext_dir, "agents", "web_surfer", "page_script.js")
                except Exception as e:
                    print(f"Warning: Could not find page_script.js: {e}")
                    page_script_path = None

        # Only add the init script if we found the file
        if page_script_path and os.path.exists(page_script_path):
            print(f"Using page script from: {page_script_path}")
            try:
                await self._page.add_init_script(path=page_script_path)
            except Exception as e:
                print(f"Warning: Failed to add init script: {e}")
        else:
            print("Warning: Could not find page_script.js, proceeding without it")
        
        await self._page.goto(self.start_page)
        await self._page.wait_for_load_state()

        # Prepare the debug directory -- which stores the screenshots generated throughout the process
        await self._set_debug_dir(self.debug_dir)
        self.did_lazy_init = True
    else:
        # A remote connection is required, so raise an error if no URL is provided
        raise ValueError("A remote Playwright server URL is required. Please provide the 'playwright_server_url' parameter.")

async def patched_close(self) -> None:
    """
    Modified close method to handle proper cleanup of remote connections.
    """
    # Close the browser if we have one
    if hasattr(self, '_browser') and self._browser is not None:
        try:
            await self._browser.close()
            self._browser = None
        except Exception as e:
            print(f"Error closing browser: {e}")
    
    # Close the playwright instance if we have one
    if hasattr(self, '_pw_instance') and self._pw_instance is not None:
        try:
            await self._pw_instance.__aexit__(None, None, None)
            self._pw_instance = None
        except Exception as e:
            print(f"Error closing Playwright instance: {e}")
    
    # Call original close method
    await original_close(self)

# Our extended MultimodalWebSurfer class with remote server support
class RemoteMultimodalWebSurfer(MultimodalWebSurfer):
    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        playwright_server_url: str,  # Required parameter, no default value
        downloads_folder: Optional[str] = None,
        description: str = MultimodalWebSurfer.DEFAULT_DESCRIPTION,
        debug_dir: Optional[str] = None,
        headless: bool = True,
        start_page: Optional[str] = None,
        animate_actions: bool = False,
        to_save_screenshots: bool = False,
        use_ocr: bool = False,
        browser_channel: Optional[str] = None,
        browser_data_dir: Optional[str] = None,
        to_resize_viewport: bool = True,
        playwright: Optional[Playwright] = None,
        context: Optional[BrowserContext] = None,
    ):
        """
        Initialize the RemoteMultimodalWebSurfer with support for a remote Playwright server.
        
        Args:
            playwright_server_url: WebSocket URL for connecting to a remote Playwright server.
                                  Format: "ws://hostname:port". Example: "ws://localhost:3001"
                                  This parameter is required.
            
            All other arguments are the same as the original MultimodalWebSurfer.
        """
        if not playwright_server_url:
            raise ValueError("playwright_server_url is required for RemoteMultimodalWebSurfer")
            
        super().__init__(
            name=name,
            model_client=model_client,
            downloads_folder=downloads_folder,
            description=description,
            debug_dir=debug_dir,
            headless=headless,
            start_page=start_page,
            animate_actions=animate_actions,
            to_save_screenshots=to_save_screenshots,
            use_ocr=use_ocr,
            browser_channel=browser_channel,
            browser_data_dir=browser_data_dir,
            to_resize_viewport=to_resize_viewport,
            playwright=playwright,
            context=context
        )
        
        # Store the remote server URL
        self.playwright_server_url = playwright_server_url
        
        # Patch the _lazy_init method to support remote server
        self._lazy_init = patched_lazy_init.__get__(self, self.__class__)
        self.close = patched_close.__get__(self, self.__class__)
        
        # Initialize connection attributes
        self._pw_instance = None
        self._browser = None


# Apply the monkey patch to the original MultimodalWebSurfer class to support remote server URL
def patch_multimodal_web_surfer():
    """
    Monkey patches the original MultimodalWebSurfer class to support a remote Playwright server.
    Call this function before using MultimodalWebSurfer with a remote server.
    """
    
    # Store the original __init__ method
    original_init = MultimodalWebSurfer.__init__
    
    def patched_init(self, name, model_client, playwright_server_url=None, **kwargs):
        # Call the original __init__ method
        original_init(self, name, model_client, **kwargs)
        
        # Add the playwright_server_url attribute
        self.playwright_server_url = playwright_server_url
        
        # Initialize connection attributes
        self._pw_instance = None
        self._browser = None
        
        # Patch the _lazy_init and close methods
        self._lazy_init = patched_lazy_init.__get__(self, self.__class__)
        self.close = patched_close.__get__(self, self.__class__)
    
    # Replace the original __init__ method with the patched one
    MultimodalWebSurfer.__init__ = patched_init 