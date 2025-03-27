# pip install -U autogen-agentchat autogen-ext[openai,web-surfer]
# playwright install
import asyncio
import os
from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from typing import Optional

# Import our custom implementation with remote server support
from custom_web_surfer import RemoteMultimodalWebSurfer

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    
    # Get the server URL from environment variable or use default
    # Two types of URLs are supported:
    # 1. WebSocket URLs (ws://): Connect to a remote Playwright server
    #    Example: ws://your-playwright-server.example.com
    # 2. HTTP URLs (http://): Connect to a Chrome browser with remote debugging
    #    Example: http://localhost:9222
    #
    # For a remote cloud-hosted Playwright server, use a WebSocket URL
    playwright_server_url = os.environ.get("PLAYWRIGHT_SERVER_URL", "ws://localhost:3001")
    
    # Get headless mode from environment variable or default to True
    # This matters for local browser instances but not for remote connections
    headless_str = os.environ.get("HEADLESS", "true").lower()
    headless = headless_str != "false"  # Default to True unless explicitly set to "false"
    
    print(f"Connecting to remote browser at: {playwright_server_url}")
    print(f"Headless mode: {headless}")
    
    try:
        # Use the RemoteMultimodalWebSurfer class to connect to a remote browser
        web_surfer = RemoteMultimodalWebSurfer(
            "web_surfer", 
            model_client, 
            playwright_server_url=playwright_server_url,  # URL to remote server
            headless=headless,  # Only matters for local browser fallbacks
            animate_actions=True
        )
        
        # The user proxy agent is used to get user input after each step of the web surfer.
        # NOTE: you can skip input by pressing Enter.
        user_proxy = UserProxyAgent("user_proxy")
        # The termination condition is set to end the conversation when the user types 'exit'.
        termination = TextMentionTermination("exit", sources=["user_proxy"])
        # Web surfer and user proxy take turns in a round-robin fashion.
        team = RoundRobinGroupChat([web_surfer, user_proxy], termination_condition=termination)
        
        # Start the team and wait for it to terminate.
        await Console(team.run_stream(task="Find information about AutoGen and write a short summary."))
    except ConnectionError as e:
        print(f"ERROR: Connection to remote browser failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. For WebSocket URLs: Make sure a Playwright server is running at the specified URL")
        print("2. For HTTP URLs: Make sure Chrome is running with --remote-debugging-port flag")
        print("3. Check network connectivity and any firewalls that might block the connection")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if 'web_surfer' in locals():
            await web_surfer.close()
        await model_client.close()

asyncio.run(main())