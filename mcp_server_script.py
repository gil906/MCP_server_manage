from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Literal, Optional

import docker
import psutil
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP(name="Raspberry Pi MCP")


# -------- System Info --------
@mcp.tool()
def get_cpu_usage() -> dict:
    """Get current CPU utilization percent."""
    return {"usage_percent": psutil.cpu_percent(interval=0.2)}


@mcp.tool()
def get_memory_usage() -> dict:
    """Get memory usage in bytes and percent."""
    mem = psutil.virtual_memory()
    return {
        "total_bytes": int(mem.total),
        "used_bytes": int(mem.used),
        "available_bytes": int(mem.available),
        "percent": float(mem.percent),
    }


# -------- Docker helpers --------

def _docker() -> docker.DockerClient:
    return docker.from_env()


@mcp.tool()
def list_containers(all: bool = True) -> dict:
    """List Docker containers (id, name, status, image)."""
    try:
        client = _docker()
        items = []
        for c in client.containers.list(all=all):
            items.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "status": getattr(c, "status", "unknown"),
                    "image": c.image.tags[0] if c.image.tags else str(c.image.short_id),
                }
            )
        return {"containers": items}
    except Exception as e:  # pragma: no cover - surface error to user
        return {"error": str(e)}


@mcp.tool()
def container_logs(name: str, tail: int = 100) -> dict:
    """Get the last N log lines from a container."""
    try:
        client = _docker()
        c = client.containers.get(name)
        logs = c.logs(tail=tail).decode("utf-8", errors="replace")
        return {"name": c.name, "tail": tail, "logs": logs}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_container(image: str, name: str, command: Optional[str] = None, detach: bool = True) -> dict:
    """Create and start a container from an image."""
    try:
        client = _docker()
        container = client.containers.run(image, name=name, command=command, detach=detach)
        return {"created": True, "id": container.id, "name": container.name}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def delete_container(name: str, force: bool = True) -> dict:
    """Delete a container by name."""
    try:
        client = _docker()
        c = client.containers.get(name)
        c.remove(force=force)
        return {"deleted": True, "name": name}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def stop_container(name: str, timeout: int = 10) -> dict:
    """Stop a container by name."""
    try:
        client = _docker()
        c = client.containers.get(name)
        c.stop(timeout=timeout)
        return {"stopped": True, "name": name}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def start_container(name: str) -> dict:
    """Start a container by name."""
    try:
        client = _docker()
        c = client.containers.get(name)
        c.start()
        return {"started": True, "name": name}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def restart_container(name: str) -> dict:
    """Restart a container by name."""
    try:
        client = _docker()
        c = client.containers.get(name)
        c.restart()
        return {"restarted": True, "name": name}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def inspect_container(name: str) -> dict:
    """Return low-level information about a container."""
    try:
        client = _docker()
        c = client.containers.get(name)
        return {"name": c.name, "attrs": c.attrs}
    except Exception as e:
        return {"error": str(e)}


# -------- Crontab --------
@mcp.tool()
def create_crontab_task(schedule: str, command: str) -> dict:
    """Append a cron entry to the user's crontab. Requires writable crontab mount on host."""
    try:
        # Combine existing crontab (if any) with the new line
        line = f"{schedule} {command}"
        cmd = f'(crontab -l 2>/dev/null; echo "{line}") | crontab -'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return {"created": True, "entry": line}
        return {"error": result.stderr.strip() or "failed to write crontab"}
    except Exception as e:
        return {"error": str(e)}


# -------- Filesystem --------
@mcp.tool()
def list_files(folder: str = "/mnt/media") -> dict:
    """List files in a folder."""
    try:
        return {"folder": folder, "files": sorted(os.listdir(folder))}
    except Exception as e:
        return {"error": str(e)}


# -------- Network utilities (may require extra container capabilities) --------
@mcp.tool()
def network_test(target: str = "8.8.8.8", count: int = 4) -> dict:
    """Ping a target host or IP."""
    try:
        result = subprocess.run(["ping", "-c", str(count), target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return {"ok": True, "output": result.stdout}
        return {"error": result.stderr or result.stdout}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_virtual_ip(ip: str, interface: str = "eth0") -> dict:
    """Add a virtual IP to an interface. Requires NET_ADMIN and host networking to affect the host."""
    try:
        result = subprocess.run(["ip", "addr", "add", ip, "dev", interface], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return {"ok": True, "message": f"Added {ip} to {interface}"}
        return {"error": result.stderr.strip() or result.stdout.strip()}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def iptables_rule(action: Literal["add", "remove"], port: int, protocol: str = "tcp") -> dict:
    """Add or remove an iptables ACCEPT rule on INPUT for a port/protocol. Requires NET_ADMIN."""
    try:
        if action == "add":
            cmd = ["iptables", "-A", "INPUT", "-p", protocol, "--dport", str(port), "-j", "ACCEPT"]
        else:
            cmd = ["iptables", "-D", "INPUT", "-p", protocol, "--dport", str(port), "-j", "ACCEPT"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return {"ok": True, "message": f"{action} rule for {port}/{protocol}"}
        return {"error": result.stderr.strip() or result.stdout.strip()}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Expose Streamable HTTP transport on /mcp so VS Code can connect via HTTP
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8082)
