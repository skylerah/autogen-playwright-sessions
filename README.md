# Remote Playwright Server for MultimodalWebSurfer

This project extends the AutoGen MultimodalWebSurfer to support remote Playwright servers, focusing on containerized environments.

## Overview

The standard MultimodalWebSurfer creates a local browser instance. This extended implementation requires a remote Playwright server, which is ideal for:

1. Running browser automation in containerized environments
2. Separating browser resources from application logic
3. Distributed or microservice architectures
4. Cloud deployments where the browser needs to run separately

## Components

- `custom_web_surfer.py`: Contains the patched RemoteMultimodalWebSurfer implementation
- `agent.py`: Demo script showing how to use the remote implementation
- `docker-compose.yml`: Docker Compose configuration for running both server and client
- `Dockerfile`: Container definition for the web surfer client
- `page_script.js`: JavaScript used by the web surfer to initialize pages

## Requirements

For local development:
- Python 3.8+
- AutoGen (autogen-agentchat and autogen-ext)
- Playwright

```bash
pip install -r requirements.txt
playwright install

# Copy the page_script.js file from the package if not already present
cp $(python -c "import os, autogen_ext; print(os.path.join(os.path.dirname(autogen_ext.__file__), 'agents', 'web_surfer', 'page_script.js'))") .
```

For containerized deployment:
- Docker
- Docker Compose

## Usage

### Running with Docker Compose

The easiest way to run the entire stack is with Docker Compose:

```bash
docker-compose up -d
```

This starts:
1. A Playwright server container (`playwright-server`)
2. The AutoGen web surfer client (`web-surfer`)

The client automatically connects to the server using the environment variable `PLAYWRIGHT_SERVER_URL`.

### Manual Setup

#### 1. Start the Playwright Server

Start a Playwright server using the provided script or directly with npx:

```bash
# Using npx
npx playwright run-server --port=3001
```

#### 2. Run the Agent

Set the environment variables to point to your server and configure headless mode:

```bash
# Set the server URL
export PLAYWRIGHT_SERVER_URL=ws://localhost:3001

# Enable headless mode (no browser UI)
export HEADLESS=true

# Run the agent
python agent.py
```

### Configuration

You can configure the agent using environment variables:

1. `PLAYWRIGHT_SERVER_URL`: WebSocket URL to the Playwright server (default: ws://localhost:3001)
2. `HEADLESS`: Whether to run the browser in headless mode (default: true)
   - Set to "true" for headless operation (no browser UI)
   - Set to "false" to see the browser UI (useful for debugging)

These can be configured in several ways:
- In the Docker Compose file
- Through environment variables when running manually
- By editing the defaults in `agent.py`

## How It Works

The implementation requires a `playwright_server_url` parameter and enforces remote connections:

1. The RemoteMultimodalWebSurfer class requires a WebSocket URL to connect to
2. It uses the Playwright client to connect to the remote server
3. No fallback to local browser is provided - remote connection is mandatory

## Troubleshooting

If you encounter issues:

1. Check container logs: `docker-compose logs playwright-server`
2. Ensure the Playwright server is running: `docker ps`
3. Verify network connectivity between containers
4. Check for firewall issues if running across different hosts
5. Set `HEADLESS=false` temporarily to see the browser UI and debug issues
6. Make sure the `page_script.js` file is present in your project directory
7. Check file permissions on the `page_script.js` file (should be readable)

## Potential Issues

- Ensure the server is fully initialized before the client tries to connect
- Network latency between containers can affect performance
- If running in a complex network setup, ensure proper routing between containers
- In headless mode, screenshots may behave differently than in headed mode
- Missing `page_script.js` file will cause initialization errors 