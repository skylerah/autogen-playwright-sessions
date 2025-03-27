# Remote Playwright Server for MultimodalWebSurfer

This project extends the AutoGen MultimodalWebSurfer to support remote browser connections, focusing on cloud and containerized environments.

## Overview

The standard MultimodalWebSurfer creates a local browser instance. This extended implementation provides two approaches for using remote browsers:

1. **WebSocket URLs (ws://)**: Connect to a remote Playwright server
2. **HTTP/HTTPS URLs (http://)**: Connect to a Chrome browser with remote debugging enabled

Both approaches allow you to separate the browser from your application code, which is ideal for cloud deployments.

## Components

- `custom_web_surfer.py`: Contains the patched RemoteMultimodalWebSurfer implementation
- `agent.py`: Demo script showing how to use the remote implementation
- `docker-compose.yml`: Docker Compose configuration for running both server and client
- `Dockerfile`: Container definition for the web surfer client
- `page_script.js`: Required JavaScript file for browser initialization (copied from autogen_ext package)
- `test.py`: Example of connecting to a remote Playwright server

## Requirements

For local development:
- Python 3.8+
- AutoGen (autogen-agentchat and autogen-ext)
- Playwright

```bash
pip install -r requirements.txt
playwright install
```

For remote deployment:
- Docker
- Docker Compose (optional)
- A remote Playwright server or Chrome browser with remote debugging

## Setup

### Required Files

The `page_script.js` file is required for the MultimodalWebSurfer to function correctly. This file should be in your project directory. If it's not there:

1. It will be automatically copied from the autogen_ext package (if found)
2. You can manually copy it using this command:
   ```bash
   python -c "import os, shutil, autogen_ext; src = os.path.join(os.path.dirname(autogen_ext.__file__), 'agents', 'web_surfer', 'page_script.js'); shutil.copy(src, 'page_script.js')"
   ```
3. The Dockerfile automatically handles this for container builds

To verify that the files are correctly set up, run:
```bash
python check_files.py
```

## Usage

### Option 1: Connect to a Remote Playwright Server (WebSocket)

This approach connects to a standalone Playwright server running remotely:

1. **Deploy a Playwright server** in the cloud:
   ```bash
   # On your cloud server
   npx playwright run-server --port=3001
   ```

2. **Run your client** with the WebSocket URL:
   ```bash
   # Set the WebSocket URL to your remote server
   export PLAYWRIGHT_SERVER_URL=ws://your-playwright-server.example.com
   python agent.py
   ```

### Option 2: Connect to a Remote Chrome Browser (HTTP)

This approach connects to a Chrome/Chromium browser with remote debugging:

1. **Start Chrome with remote debugging** in the cloud:
   ```bash
   # On your cloud server
   google-chrome --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --headless=new
   ```

2. **Run your client** with the HTTP URL:
   ```bash
   # Set the HTTP URL to your remote Chrome
   export PLAYWRIGHT_SERVER_URL=http://your-chrome-server.example.com:9222
   python agent.py
   ```

### Running with Docker Compose

For local testing, you can use Docker Compose to run both server and client:

```bash
docker-compose up -d
```

This starts:
1. A Playwright server container (`playwright-server`)
2. The AutoGen web surfer client (`web-surfer`)

### Configuration

You can configure the agent using environment variables:

1. `PLAYWRIGHT_SERVER_URL`: URL for browser connection
   - WebSocket URL for Playwright servers: `ws://hostname:port`
   - HTTP URL for Chrome browsers: `http://hostname:port`

2. `HEADLESS`: Whether to run the browser in headless mode (default: true)
   - Only applies to local browser instances
   - Set to "false" to see the browser UI (useful for debugging)

3. `DEBUG`: Set to "pw:api" to enable verbose Playwright logging

## How It Works

There are two connection modes supported by the implementation:

### 1. WebSocket URL Mode (Playwright Server)
When you provide a WebSocket URL like `ws://your-server:3001`:
- Connects to a remote Playwright server
- The browser instance is managed by the remote server
- Works with standalone Playwright servers running in the cloud
- Example shown in `test.py`

### 2. HTTP URL Mode (CDP)
When you provide an HTTP URL like `http://your-chrome:9222`:
- Connects to a running Chrome/Edge browser with remote debugging enabled
- Uses Chrome DevTools Protocol (CDP) to control the browser
- Works with browsers launched with `--remote-debugging-port` flag

## Cloud Deployment

To deploy a headless browser in the cloud:

1. **Create a VM or container** with Playwright installed
2. **Run the Playwright server**: `npx playwright run-server --port=3001`
3. **Expose the port** securely (consider using a reverse proxy with authentication)
4. **Connect from your client** using the WebSocket URL

## Troubleshooting

If you encounter issues:

1. **Connection errors**: Ensure the remote server is running and accessible
2. **Network issues**: Check firewalls, VPNs, or network policies that might block WebSocket connections
3. **Missing page_script.js**: Ensure this file is properly copied to your project
4. **Browser not launching**: Check resource constraints in your cloud environment

### Common Issues

- **Connection refused**: The server isn't running or the port isn't accessible
- **WebSocket handshake failed**: Network issues or incorrect URL
- **Browser crashes**: Not enough memory or resources in your container/VM
- **Missing page_script.js**: Copy it from the autogen_ext package as described above

## Technical Notes

For production deployments, consider:
1. Adding authentication to your Playwright server
2. Using HTTPS/WSS for secure connections
3. Setting resource limits for browser instances
4. Implementing proper logging and monitoring 