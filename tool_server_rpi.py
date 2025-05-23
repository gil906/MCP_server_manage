import fastapi
import uvicorn
import subprocess
import docker
import os  # Added for environment variable access
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

app = fastapi.FastAPI()

# --- Configuration ---
API_KEY = os.getenv("API_KEY")  # Read API_KEY from environment variable
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

if not API_KEY:
    raise RuntimeError("API_KEY environment variable not set. The server will not start.")

# --- Security ---
async def get_api_key(key: str = Security(api_key_header)):
    if key == API_KEY:
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
            return [{"id": c.short_id, "name": c.name, "image": c.attrs['Config']['Image'], "status": c.status} for c in containers]
        elif action == "list_images":
            images = client.images.list()
            return [{"id": img.short_id, "tags": img.tags} for img in images]
        elif action == "run_container":
            if not image_name:
                raise HTTPException(status_code=400, detail="image_name is required to run a container")
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
            return {"logs": container.logs(tail=50).decode('utf-8')}  # Get last 50 lines
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
    if not command:  # Basic validation
        raise HTTPException(status_code=400, detail="Command cannot be empty.")

    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=30)  # 30 second timeout

        if process.returncode == 0:
            return {"output": stdout.strip()}
        else:
            return {"error": stderr.strip(), "return_code": process.returncode, "output": stdout.strip()}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing command: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
