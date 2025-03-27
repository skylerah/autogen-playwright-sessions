import asyncio
import sys
import warnings
import os
import urllib.parse
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

        try:
            # Create the playwright instance connecting to remote server
            if self._playwright is None:
                # Start playwright
                self._pw_instance = await async_playwright().__aenter__()
                
                # Parse the URL to determine connection type
                parsed_url = urllib.parse.urlparse(self.playwright_server_url)
                
                # Launch browser based on the URL type
                if parsed_url.scheme == "ws":
                    print(f"Connecting to remote Playwright server at: {self.playwright_server_url}")
                    
                    # Connect to the remote Playwright server using WebSockets
                    # This approach works with a standalone Playwright server running in the cloud
                    try:
                        self._playwright = self._pw_instance
                        browser = await self._playwright.chromium.connect(self.playwright_server_url)
                        self._browser = browser
                        print(f"Successfully connected to remote Playwright server")
                    except Exception as e:
                        raise ConnectionError(f"Failed to connect to remote Playwright server: {e}")
                        
                elif parsed_url.scheme in ["http", "https"]:
                    # For HTTP URLs, connect to a CDP endpoint
                    # This works with Chrome/Edge browsers with remote debugging enabled
                    print(f"Connecting to CDP endpoint at: {self.playwright_server_url}")
                    self._playwright = self._pw_instance
                    browser = await self._playwright.chromium.connect_over_cdp(self.playwright_server_url)
                    self._browser = browser
                else:
                    raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}. Use ws:// or http:// URLs.")
                    
            # Create the context
            if self._context is None and self._browser is not None:
                self._context = await self._browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
                )
            else:
                raise ValueError("Browser initialization failed. Check the connection to the remote Playwright server.")

            # Create the page
            self._context.set_default_timeout(60000)  # One minute
            self._page = await self._context.new_page()
            assert self._page is not None
            self._page.on("download", self._download_handler)
            if self.to_resize_viewport:
                await self._page.set_viewport_size({"width": self.VIEWPORT_WIDTH, "height": self.VIEWPORT_HEIGHT})
            
            # Add the initialization script using the local copy
            # First check if we have a local copy of the script
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_script.js")
            
            # If not found locally, try to use the one from autogen_ext package
            if not os.path.exists(script_path):
                try:
                    import autogen_ext
                    package_dir = os.path.dirname(autogen_ext.__file__)
                    script_path = os.path.join(package_dir, "agents", "web_surfer", "page_script.js")
                    print(f"Using package script from: {script_path}")
                except Exception as e:
                    print(f"Warning: Could not find page_script.js: {e}")
                    # Try to continue without the script
                    script_path = None
            
            # Add the init script if found
            if script_path and os.path.exists(script_path):
                print(f"Adding init script from: {script_path}")
                await self._page.add_init_script(path=script_path)
            else:
                print("Warning: page_script.js not found. Some functionality may be limited.")
                
            await self._page.goto(self.start_page)
            await self._page.wait_for_load_state()

            # Prepare the debug directory -- which stores the screenshots generated throughout the process
            await self._set_debug_dir(self.debug_dir)
            self.did_lazy_init = True
            
        except Exception as e:
            raise ConnectionError(f"Failed to initialize remote browser: {e}")
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