# Raspberry Pi AI Management Setup

This setup allows you to manage your Raspberry Pi server (including Docker containers and system commands) using an AI assistant like those accessed through OpenWebUI/LiteLLM or VS Code Copilot, with LiteLLM acting as a central proxy.

## Architecture

The communication flows as follows: You interact with a client application (OpenWebUI or VS Code). This client sends your requests to LiteLLM. LiteLLM, configured with tool definitions, determines if a task requires interacting with your Raspberry Pi. If so, LiteLLM makes a "tool call" request to the Tool Server running on your Raspberry Pi. The Tool Server then executes the command (e.g., a Docker command or a system command) and returns the result to LiteLLM, which then formulates a final response for you.

```mermaid
graph TD
    U[User] --> CLIENT{Client Application <br> (OpenWebUI / VS Code)}
    CLIENT -- "User Prompt + Tool Definitions" --> LITELLM[LiteLLM <br> (Acts as AI/LLM Proxy, <br> e.g., http://192.168.0.202:4000)]
    LITELLM -- "Tool Call Request (HTTP POST + API Key)" --> RPI_TOOL_SERVER[Raspberry Pi Tool Server <br> (FastAPI App on RPi @192.168.0.202:8080)]
    
    subgraph "Raspberry Pi (192.168.0.202)"
        RPI_TOOL_SERVER
        DOCKER_ENGINE[Host Docker Engine]
        HOST_OS[Host OS & System Commands]
    end

    RPI_TOOL_SERVER -- "Docker Commands (via /var/run/docker.sock)" --> DOCKER_ENGINE
    RPI_TOOL_SERVER -- "System Commands (executed within container context)" --> HOST_OS
    
    DOCKER_ENGINE -- Results --> RPI_TOOL_SERVER
    HOST_OS -- Results --> RPI_TOOL_SERVER
    
    RPI_TOOL_SERVER -- "Tool Execution Result (JSON)" --> LITELLM
    LITELLM -- "Final Natural Language Response" --> CLIENT
```

1.  **Client Application (OpenWebUI / VS Code)**: Your interface for interacting with the AI.
    *   **OpenWebUI**: Configured to use LiteLLM as its backend. When LiteLLM indicates a tool call, OpenWebUI (or an intermediary component you might need to set up if OpenWebUI doesn't natively execute tool calls to arbitrary HTTP endpoints) would be responsible for forwarding the tool execution request from LiteLLM to the RPi Tool Server.
    *   **VS Code**: Can interact with LiteLLM similarly, or Copilot Chat can help you write scripts/commands to call LiteLLM or even the RPi Tool Server directly for specific, non-AI-mediated tasks.
2.  **LiteLLM (AI/LLM Proxy)**: Deployed at `http://192.168.0.202:4000`.
    *   Receives requests from your client application.
    *   Is configured with tool definitions (see `litellm_tool_definitions.json`) that describe the capabilities of the RPi Tool Server.
    *   When the LLM decides to use a tool, LiteLLM structures this as a tool call. The actual HTTP request to the RPi Tool Server must be made by a component that can process LiteLLM's output (e.g., your client application, a custom script, or a feature within OpenWebUI/LiteLLM if available).
3.  **Tool Server (Raspberry Pi)**: A Python FastAPI application running on your Raspberry Pi (`192.168.0.202`), typically on port `8080`. This single server application exposes endpoints for various management tasks.
    *   `/docker_command`: Manages Docker containers (list, run, stop, etc.).
    *   `/system_command`: Executes system-level commands. **Caution is advised here due to security implications.**
    *   It's secured by an API key.

## Raspberry Pi Setup (Server-Side)

**Target IP**: `192.168.0.202`

1.  **Prerequisites**:
    *   Docker installed and running on the Raspberry Pi.
    *   Your user on the Raspberry Pi should be able to run `docker` commands (e.g., added to the `docker` group: `sudo usermod -aG docker $USER`).
    *   Python 3.8+ and `pip` (primarily if you choose not to use Docker for the Tool Server, or for building the image).

2.  **Files to Copy to Raspberry Pi** (if building Docker image on RPi or running natively):
    *   `tool_server_rpi.py`
    *   `requirements_rpi.txt`
    *   `Dockerfile` (new)
    *   `run_tool_server.sh` (will be updated, primarily for Docker)
    *   `tool_server.service` (optional, for native systemd setup)

3.  **Running the Tool Server (Recommended: Docker Container)**

    *   **a. Create a `Dockerfile`**: (A `Dockerfile` will be provided in the next steps).
    *   **b. Build the Docker Image**:
        Navigate to the directory containing the `Dockerfile`, `tool_server_rpi.py`, and `requirements_rpi.txt` on your Raspberry Pi.
        ```bash
        docker build -t rpi-tool-server .
        ```
    *   **c. Run the Docker Container**:
        You'll need to provide a strong API key.
        ```bash
        # Generate a strong API key, e.g., using: openssl rand -hex 32
        export RPI_TOOL_SERVER_API_KEY="your_generated_super_secret_api_key"

        docker run -d \
          --name rpi-tool-server \
          -p 8080:8080 \
          -v /var/run/docker.sock:/var/run/docker.sock \
          -e API_KEY=$RPI_TOOL_SERVER_API_KEY \
          --restart unless-stopped \
          rpi-tool-server
        ```
        *   `-d`: Run in detached mode.
        *   `--name rpi-tool-server`: Assign a name to the container.
        *   `-p 8080:8080`: Map port 8080 on the host to port 8080 in the container.
        *   `-v /var/run/docker.sock:/var/run/docker.sock`: **Crucial for Docker management.** Mounts the host's Docker socket into the container, allowing the Tool Server to manage Docker on the host.
        *   `-e API_KEY=$RPI_TOOL_SERVER_API_KEY`: Passes the API key as an environment variable to the application. The `tool_server_rpi.py` script will be updated to read this.
        *   `--restart unless-stopped`: Ensures the container restarts automatically.
    *   **d. Check Logs**:
        ```bash
        docker logs rpi-tool-server
        ```
    *   **System Commands in Docker**: Commands sent to the `/system_command` endpoint will execute *inside* the container's environment. They can interact with the host's Docker daemon (via the mounted socket) but other system commands will be scoped to the container. For many diagnostic tasks this is sufficient. If you need deeper host OS interaction, this requires careful consideration of container privileges and command design, which is an advanced topic with security implications.

4.  **Alternative: Running Natively (without Docker)**
    *   **a. Install Dependencies**:
        ```bash
        ssh pi@192.168.0.202
        cd /path/to/your/tool_server_files 
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements_rpi.txt
        ```
    *   **b. Configure API Key**:
        The `tool_server_rpi.py` script will be modified to read the API key from an environment variable `API_KEY`. Set this variable in your shell before running, or in the `.service` file.
        ```bash
        export API_KEY="YOUR_SUPER_SECRET_API_KEY"
        ```
    *   **c. Run Manually**:
        ```bash
        # Ensure API_KEY is set in your environment
        python3 tool_server_rpi.py 
        # Or using the run script (which you might adapt)
        # chmod +x run_tool_server.sh
        # ./run_tool_server.sh
        ```
    *   **d. Run as a Systemd Service**: (See `tool_server.service` file to be provided; you'll need to edit paths and ensure the `API_KEY` environment variable is set within the service unit).

## LiteLLM / OpenWebUI Setup (Client-Side)

This part involves making your LLM (via LiteLLM) aware of the tools and having an application layer that calls the Tool Server.

1.  **Tool Definitions (`litellm_tool_definitions.json`)**:
    *   This file (to be provided) contains the JSON schema definitions for the tools (`/docker_command`, `/system_command`) that your LLM needs to know about.
    *   When making a call to LiteLLM (e.g., via its OpenAI-compatible `/chat/completions` endpoint from OpenWebUI or your custom client), you'll include these tool definitions in the `tools` parameter of your request.

2.  **Client Application Logic (Handling Tool Calls from LiteLLM)**:
    *   When LiteLLM decides to use a tool, it will include a `tool_calls` section in its response.
    *   Your client application (or a component integrated with OpenWebUI/LiteLLM) is responsible for:
        a.  Detecting these `tool_calls`.
        b.  Extracting the tool name (e.g., `execute_rpi_docker_command`) and arguments.
        c.  Making an HTTP `POST` request to the appropriate endpoint on your Raspberry Pi's Tool Server (e.g., `http://192.168.0.202:8080/docker_command`). This request **must** include the `X-API-Key` header with your secret API key.
        d.  Sending the JSON response from the Tool Server back to LiteLLM in a subsequent message with `role: tool` and the `tool_call_id`.
        e.  LiteLLM then uses this tool result to generate the final user-facing response.
    *   The `openwebui_or_litellm_client_example.py` (to be provided) will demonstrate this flow for a standalone Python client. You'll need to adapt this logic or find appropriate plugins/configurations for OpenWebUI.
    *   **OpenWebUI**: Check its documentation for "function calling" or "tool use" integration. It might require specific model configurations or backend settings to enable passing tool definitions to LiteLLM and handling the subsequent tool calls. If OpenWebUI directly calls LiteLLM and can't make arbitrary HTTP calls for tools, you might need an intermediary service that OpenWebUI *can* call, which then calls your RPi Tool Server. However, LiteLLM itself can be configured with a `callbacks` mechanism that might allow you to intercept tool calls and execute them.
    *   **LiteLLM**: LiteLLM's documentation on "Tool Calling" or "Function Calling" and "Callbacks" (especially `Custom LLM` callbacks or `Router Callbacks`) will be relevant. You might be able to define a callback in your LiteLLM configuration that executes the HTTP request to your RPi server when a specific tool is invoked.

3.  **API Key for RPi Tool Server**:
    *   Ensure your client application (or the component making the HTTP call to the RPi Tool Server) sends the `X-API-Key` header with the correct API key.

## VS Code Copilot Interaction

*   **Using Copilot Chat to write scripts**:
    *   You can ask Copilot Chat: "Write a Python script to list Docker containers on my server at 192.168.0.202 by calling its tool API at port 8080, endpoint /docker_command, with the action 'list_containers' and API key 'YOUR_SUPER_SECRET_API_KEY'."
*   **Developing a VS Code Extension**:
    *   This is a more involved software development task. You would use TypeScript/JavaScript to build an extension that can:
        *   Provide a UI (e.g., command palette commands, webview).
        *   Make HTTP requests to your Raspberry Pi Tool Server.
        *   Potentially integrate with Copilot APIs if you are building a "Copilot plugin" in the Microsoft ecosystem sense.

## Security - VERY IMPORTANT

*   **API Key**: The provided Tool Server uses a simple API key. Keep this key secret.
*   **Network Exposure**: The Tool Server is exposed on your local network. Ensure your network is secure. Do NOT expose this server directly to the internet without significant additional security measures (authentication, authorization, HTTPS, input validation, rate limiting, etc.).
*   **Command Execution (`/system_command`)**:
    *   The current `execute_system_command` in `tool_server_rpi.py` allows execution of commands passed to it. When run in Docker, these commands execute *within the container*. While this contains them somewhat, granting excessive permissions to the container or running arbitrary commands is still a risk.
    *   **FOR PRODUCTION OR UNTRUSTED ENVIRONMENTS, YOU MUST MODIFY THIS**:
        1.  **Option A (Safest)**: Create a predefined allowlist of safe commands. The API would take a command *name* (e.g., "get_disk_space", "get_cpu_usage") rather than the raw command string. The server then maps this name to the actual, hardcoded command.
        2.  **Option B (Still Risky)**: Implement very strict input sanitization and validation if you must allow some flexibility. This is hard to get right.
    *   The current example is for demonstration on a trusted local network. **Proceed with extreme caution.**
*   **Docker Tool**: Ensure the Docker socket or API is not overly exposed if you modify the Docker tool for more complex operations.

This README provides a comprehensive guide. The next steps will be to create the actual files.
