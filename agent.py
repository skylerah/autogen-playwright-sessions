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
    # This makes it easy to configure in Docker or other environments
    playwright_server_url = os.environ.get("PLAYWRIGHT_SERVER_URL", "ws://pw-container-1.calmground-93964b1f.eastus.azurecontainerapps.io/")
    
    # Get headless mode from environment variable or default to True
    headless = os.environ.get("HEADLESS", "true").lower() == "true"
    
    print(f"Connecting to remote Playwright server at: {playwright_server_url}")
    print(f"Headless mode: {headless}")
    
    # Use the RemoteMultimodalWebSurfer class which requires a remote server
    web_surfer = RemoteMultimodalWebSurfer(
        "web_surfer", 
        model_client, 
        playwright_server_url=playwright_server_url,  # Required parameter
        headless=headless,  # Use the headless setting from environment
        animate_actions=True
    )
    
    # The user proxy agent is used to get user input after each step of the web surfer.
    # NOTE: you can skip input by pressing Enter.
    user_proxy = UserProxyAgent("user_proxy")
    # The termination condition is set to end the conversation when the user types 'exit'.
    termination = TextMentionTermination("exit", sources=["user_proxy"])
    # Web surfer and user proxy take turns in a round-robin fashion.
    team = RoundRobinGroupChat([web_surfer, user_proxy], termination_condition=termination)
    try:
        # Start the team and wait for it to terminate.
        await Console(team.run_stream(task="Find information about AutoGen and write a short summary."))
    finally:
        await web_surfer.close()
        await model_client.close()

asyncio.run(main())