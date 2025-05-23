import fastapi
import uvicorn
import subprocess
import docker
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

app = fastapi.FastAPI()

# --- Configuration ---
EXPECTED_API_KEY = "YOUR_SUPER_SECRET_API_KEY"  # CHANGE THIS!
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# --- Security ---
async def get_api_key(key: str = Security(api_key_header)):
    if key == EXPECTED_API_KEY:
        return key
    else:
        raise HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )

# --- Docker Operations ---
@app.post("/docker_command")
async def manage_docker(action: str, container_name: str = None, image_name: str = None, api_key: str = Security(get_api_key)):
    """
    Manages Docker containers.
    Supported actions:
    - 'list_containers': Lists all running containers.
    - 'list_images': Lists all local images.
    - 'run_container': Runs a new container (requires image_name).
    - 'stop_container': Stops a running container (requires container_name).
    - 'remove_container': Removes a stopped container (requires container_name).
    - 'inspect_container': Gets details of a container (requires container_name).
    - 'get_container_logs': Gets logs of a container (requires container_name).
    """
    client = docker.from_env()
    try:
        if action == "list_containers":
            containers = client.containers.list()
            return [{"id": c.short_id, "name": c.name, "image": c.attrs[''Config''][''Image''], "status": c.status} for c in containers]
        elif action == "list_images":
            images = client.images.list()
            return [{"id": img.short_id, "tags": img.tags} for img in images]
        elif action == "run_container":
            if not image_name:
                raise HTTPException(status_code=400, detail="image_name is required to run a container")
            # Basic run, for more complex scenarios (ports, volumes, etc.), this needs expansion
            container = client.containers.run(image_name, detach=True)
            return {"id": container.short_id, "name": container.name, "status": "started"}
        elif action == "stop_container":
            if not container_name:
                raise HTTPException(status_code=400, detail="container_name is required to stop a container")
            container = client.containers.get(container_name)
            container.stop()
            return {"id": container.short_id, "name": container.name, "status": "stopped"}
        elif action == "remove_container":
            if not container_name:
                raise HTTPException(status_code=400, detail="container_name is required to remove a container")
            container = client.containers.get(container_name)
            container.remove()
            return {"id": container.short_id, "name": container.name, "status": "removed"}
        elif action == "inspect_container":
            if not container_name:
                raise HTTPException(status_code=400, detail="container_name is required to inspect a container")
            container = client.containers.get(container_name)
            return container.attrs
        elif action == "get_container_logs":
            if not container_name:
                raise HTTPException(status_code=400, detail="container_name is required to get container logs")
            container = client.containers.get(container_name)
            return {"logs": container.logs(tail=50).decode('utf-8')} # Get last 50 lines
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported Docker action: {action}")
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container or image not found: {container_name or image_name}")
    except docker.errors.APIError as e:
        raise HTTPException(status_code=500, detail=f"Docker API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# --- System Commands ---
@app.post("/system_command")
async def execute_system_command(command: str, api_key: str = Security(get_api_key)):
    """
    Executes a predefined system command.
    WARNING: This is a powerful endpoint. For security, it's highly recommended to
    replace this with a mechanism that only allows specific, predefined commands.
    Example: command = "df -h" or "ps aux | head -n 10"
    """
    # SECURITY WARNING: Executing arbitrary commands is dangerous.
    # Consider implementing an allowlist of commands.
    # For example:
    # allowed_commands = {
    # "disk_space": "df -h",
    # "cpu_usage_top": "ps aux --sort=-%cpu | head -n 10",
    # "memory_usage_top": "ps aux --sort=-%mem | head -n 10",
    # "open_ports": "ss -tulnp"
    # }
    # if command_name in allowed_commands:
    #     actual_command = allowed_commands[command_name]
    # else:
    #     raise HTTPException(status_code=400, detail="Unsupported system command")

    if not command: # Basic validation
        raise HTTPException(status_code=400, detail="Command cannot be empty.")

    # Be extremely careful with shell=True. It can be a security risk if `command` is user-supplied directly.
    # The allowlist approach mentioned above is much safer.
    try:
        # Using shell=True is generally discouraged if the command string comes from an untrusted source.
        # If you must use it, ensure the command is from a trusted, controlled source (e.g., predefined list).
        # For this example, we assume the AI will be instructed to use safe, known commands.
        # Splitting the command into a list of arguments is safer if shell=False can be used.
        # However, for complex commands with pipes, shell=True might be needed.
        
        # Example of a safer way if you don't need shell features like pipes for all commands:
        # result = subprocess.run(command.split(), capture_output=True, text=True, check=False, timeout=30)

        # For commands that might include pipes (e.g., "ps aux | grep python")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=30) # 30 second timeout

        if process.returncode == 0:
            return {"output": stdout.strip()}
        else:
            return {"error": stderr.strip(), "return_code": process.returncode, "output": stdout.strip()}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing command: {str(e)}")

if __name__ == "__main__":
    # It's recommended to run Uvicorn directly for more control in production,
    # e.g., uvicorn tool_server_rpi:app --host 0.0.0.0 --port 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
