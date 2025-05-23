# Raspberry Pi AI Management Setup

This setup allows you to manage your Raspberry Pi server (including Docker containers and system commands) using an AI assistant like those accessed through OpenWebUI/LiteLLM or VS Code Copilot.

## Architecture

1.  **Tool Server (Raspberry Pi)**: A Python FastAPI application runs on your Raspberry Pi (192.168.0.202). It exposes secure API endpoints for:
    *   Executing predefined system commands.
    *   Managing Docker containers.
2.  **LiteLLM/OpenWebUI**:
    *   Your LLM (via LiteLLM) is informed about the available tools (e.g., `execute_docker_command`, `execute_system_command`) and their expected inputs/outputs using the OpenAI function calling/tool usage format.
    *   When you ask the AI to perform an action (e.g., "list running Docker containers"), the LLM will request the use of a specific tool.
    *   The client application (e.g., OpenWebUI, if it supports this, or a custom script using LiteLLM) is responsible for:
        1.  Receiving the tool call request from the LLM.
        2.  Making an HTTP request to the appropriate endpoint on your Raspberry Pi's Tool Server.
        3.  Sending the tool's output back to the LLM to get a final natural language response.
3.  **VS Code Copilot**:
    *   **Option 1 (Advanced)**: Develop a custom VS Code extension that acts as a client to the Raspberry Pi Tool Server API. This extension could provide commands or a chat interface to manage the server.
    *   **Option 2 (Simpler)**: Use VS Code Copilot Chat to help you:
        *   Write Python scripts that interact with the Tool Server's API.
        *   Generate `curl` commands or other CLI commands to interact with the Tool Server.

## Raspberry Pi Setup (Server-Side)

**Target IP**: `192.168.0.202`

1.  **Prerequisites**:
    *   Python 3.8+ and `pip`.
    *   Docker installed and running.
    *   Ensure your user can run `docker` commands (e.g., user is in the `docker` group).

2.  **Copy Files to Raspberry Pi**:
    *   `tool_server_rpi.py`
    *   `requirements_rpi.txt`
    *   `run_tool_server.sh`
    *   `tool_server.service` (optional, for running as a systemd service)

3.  **Install Dependencies**:
    ```bash
    ssh pi@192.168.0.202
    cd /path/to/your/tool_server_files # Navigate to where you copied the files
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements_rpi.txt
    ```

4.  **Configure API Key**:
    *   Edit `tool_server_rpi.py` and change `EXPECTED_API_KEY = "YOUR_SUPER_SECRET_API_KEY"` to a strong, unique key.

5.  **Run the Tool Server**:
    *   **Manually (for testing)**:
        ```bash
        chmod +x run_tool_server.sh
        ./run_tool_server.sh
        ```
        The server will typically run on `http://0.0.0.0:8080`. You'll access it via `http://192.168.0.202:8080`.
    *   **As a Systemd Service (Recommended for persistence)**:
        1.  Edit `tool_server.service`:
            *   Update `User=` to your username on the Raspberry Pi.
            *   Update `WorkingDirectory=` and `ExecStart=` to the correct paths where you placed the files and the `uvicorn` executable (likely `venv/bin/uvicorn`).
        2.  Copy the service file:
            ```bash
            sudo cp tool_server.service /etc/systemd/system/tool_server.service
            ```
        3.  Enable and start the service:
            ```bash
            sudo systemctl daemon-reload
            sudo systemctl enable tool_server.service
            sudo systemctl start tool_server.service
            sudo systemctl status tool_server.service # To check status
            ```

## LiteLLM / OpenWebUI Setup (Client-Side)

This part involves making your LLM (via LiteLLM) aware of the tools and having an application layer that calls the Tool Server.

1.  **Tool Definitions (`litellm_tool_definitions.json`)**:
    *   This file (provided) contains the JSON schema definitions for the tools that your LLM needs to know about.
    *   When making a call to LiteLLM (e.g., via its OpenAI-compatible `/chat/completions` endpoint), you'll include these tool definitions in the `tools` parameter of your request.

2.  **Client Application Logic (`openwebui_or_litellm_client_example.py`)**:
    *   The provided example script shows conceptually how a Python application using LiteLLM would:
        a.  Send a user's prompt to LiteLLM, along with the tool definitions.
        b.  If the LLM responds with a `tool_calls` message (indicating it wants to use a tool), the script extracts the tool name and arguments.
        c.  The script then makes an HTTP `POST` request to the appropriate endpoint on your Raspberry Pi's Tool Server (e.g., `http://192.168.0.202:8080/docker_command`), including the API key in the headers.
        d.  The response from the Tool Server is then sent back to LiteLLM (in a subsequent API call) as the result of the tool execution.
        e.  LiteLLM/LLM processes this tool result and provides a final answer to the user.
    *   **OpenWebUI**: You'll need to check OpenWebUI's documentation or community resources for how to integrate custom tool calling. It might involve:
        *   Configuring OpenWebUI to pass tool definitions to LiteLLM.
        *   A mechanism within OpenWebUI (or a plugin) that can execute the HTTP calls to your RPi Tool Server when a tool is requested by the LLM.
        *   If OpenWebUI doesn't directly support this client-side tool execution logic, you might need to place a small intermediary service (like the example script, but running as a server) between OpenWebUI and LiteLLM, or between LiteLLM and your LLM, to handle the tool calls.
    *   **LiteLLM**: If you are building a custom application with LiteLLM, you implement this tool-calling orchestration yourself, as shown in the example script.

3.  **LiteLLM Configuration for API Key**:
    *   Ensure your client application (or OpenWebUI's configuration if it handles the HTTP calls) sends the `X-API-Key` header with the correct API key when calling your Raspberry Pi Tool Server.

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
    *   The current `execute_system_command` in `tool_server_rpi.py` is **VERY DANGEROUS** as it can execute arbitrary commands.
    *   **FOR PRODUCTION OR UNTRUSTED ENVIRONMENTS, YOU MUST MODIFY THIS**:
        1.  **Option A (Safest)**: Create a predefined allowlist of safe commands. The API would take a command *name* (e.g., "get_disk_space", "get_cpu_usage") rather than the raw command string. The server then maps this name to the actual, hardcoded command.
        2.  **Option B (Still Risky)**: Implement very strict input sanitization and validation if you must allow some flexibility. This is hard to get right.
    *   The current example is for demonstration on a trusted local network. **Proceed with extreme caution.**
*   **Docker Tool**: Ensure the Docker socket or API is not overly exposed if you modify the Docker tool for more complex operations.

This README provides a comprehensive guide. The next steps will be to create the actual files.
