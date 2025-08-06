from flask import Flask, request, jsonify
import psutil
import docker
import subprocess

app = Flask(__name__)

@app.route('/get_cpu_usage', methods=['GET'])
def get_cpu_usage():
    cpu = psutil.cpu_percent()
    return jsonify({"status": "success", "result": f"CPU usage: {cpu}%"})

@app.route('/get_memory_usage', methods=['GET'])
def get_memory_usage():
    mem = psutil.virtual_memory()
    return jsonify({"status": "success", "result": f"Memory usage: {mem.used / (1024 ** 3):.2f}GB / {mem.total / (1024 ** 3):.2f}GB"})

@app.route('/create_container', methods=['POST'])
def create_container():
    data = request.get_json()
    image = data.get('image')
    name = data.get('name')
    if not image or not name:
        return jsonify({"status": "error", "message": "Missing image or name"}), 400
    try:
        client = docker.from_env()
        client.containers.run(image, name=name, detach=True)
        return jsonify({"status": "success", "result": f"Container {name} created with image {image}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/create_crontab_task', methods=['POST'])
def create_crontab_task():
    data = request.get_json()
    schedule = data.get('schedule')
    command = data.get('command')
    if not schedule or not command:
        return jsonify({"status": "error", "message": "Missing schedule or command"}), 400
    try:
        subprocess.run(f'(crontab -l 2>/dev/null; echo "{schedule} {command}") | crontab -', shell=True)
        return jsonify({"status": "success", "result": f"Crontab task created: {schedule} {command}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET", "POST"])
def root():
    if request.method == "POST":
        try:
            data = request.get_json(force=True, silent=True)
            if data and data.get("method") == "initialize":
                # Respond with MCP-like capabilities and tools for VS Code
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": data.get("id", 1),
                    "result": {
                        "capabilities": {
                            "serverName": "MCP Python Server",
                            "version": "1.0.0",
                            "features": [
                                "cpu_usage", "memory_usage", "container_management", "crontab", "file_listing", "network_test", "virtual_ip", "iptables"
                            ],
                            "tools": [
                                {"name": "get_cpu_usage", "description": "Get CPU usage"},
                                {"name": "get_memory_usage", "description": "Get memory usage"},
                                {"name": "create_container", "description": "Create a new Docker container"},
                                {"name": "delete_container", "description": "Delete a Docker container"},
                                {"name": "stop_container", "description": "Stop a Docker container"},
                                {"name": "start_container", "description": "Start a Docker container"},
                                {"name": "restart_container", "description": "Restart a Docker container"},
                                {"name": "inspect_container", "description": "Inspect a Docker container"},
                                {"name": "container_logs", "description": "Get logs from a Docker container"},
                                {"name": "list_containers", "description": "List all Docker containers"},
                                {"name": "create_crontab_task", "description": "Create a crontab task"},
                                {"name": "list_files", "description": "List files in a directory"},
                                {"name": "network_test", "description": "Run a network test (ping)"},
                                {"name": "create_virtual_ip", "description": "Create a virtual IP on the host"},
                                {"name": "iptables_rule", "description": "Add or remove iptables rules for ports"}
                            ]
                        }
                    }
                })
            else:
                return jsonify({"status": "success", "message": "MCP Server is running (POST)"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "success", "message": "MCP Server is running (GET)"})

@app.route('/list_containers', methods=['GET'])
def list_containers():
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        result = []
        for c in containers:
            result.append({
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "image": str(c.image.tags)
            })
        return jsonify({"status": "success", "containers": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/container_logs', methods=['GET'])
def container_logs():
    container_name = request.args.get('name')
    tail = int(request.args.get('tail', 100))
    if not container_name:
        return jsonify({"status": "error", "message": "Missing container name"}), 400
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        logs = container.logs(tail=tail).decode('utf-8')
        return jsonify({"status": "success", "logs": logs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/create_virtual_ip', methods=['POST'])
def create_virtual_ip():
    data = request.get_json()
    ip = data.get('ip')
    interface = data.get('interface', 'eth0')
    if not ip:
        return jsonify({"status": "error", "message": "Missing IP address"}), 400
    try:
        result = subprocess.run(["sudo", "ip", "addr", "add", ip, "dev", interface], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return jsonify({"status": "success", "message": f"Virtual IP {ip} added to {interface}"})
        else:
            return jsonify({"status": "error", "message": result.stderr}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/list_files', methods=['GET'])
def list_files():
    import os
    folder = request.args.get('folder', '/mnt/media')
    try:
        files = os.listdir(folder)
        return jsonify({"status": "success", "files": files})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/network_test', methods=['GET'])
def network_test():
    import subprocess
    target = request.args.get('target', '8.8.8.8')
    try:
        result = subprocess.run(["ping", "-c", "4", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return jsonify({"status": "success", "output": result.stdout})
        else:
            return jsonify({"status": "error", "output": result.stderr}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete_container', methods=['POST'])
def delete_container():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"status": "error", "message": "Missing container name"}), 400
    try:
        client = docker.from_env()
        container = client.containers.get(name)
        container.remove(force=True)
        return jsonify({"status": "success", "result": f"Container {name} deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stop_container', methods=['POST'])
def stop_container():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"status": "error", "message": "Missing container name"}), 400
    try:
        client = docker.from_env()
        container = client.containers.get(name)
        container.stop()
        return jsonify({"status": "success", "result": f"Container {name} stopped"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/start_container', methods=['POST'])
def start_container():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"status": "error", "message": "Missing container name"}), 400
    try:
        client = docker.from_env()
        container = client.containers.get(name)
        container.start()
        return jsonify({"status": "success", "result": f"Container {name} started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/restart_container', methods=['POST'])
def restart_container():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"status": "error", "message": "Missing container name"}), 400
    try:
        client = docker.from_env()
        container = client.containers.get(name)
        container.restart()
        return jsonify({"status": "success", "result": f"Container {name} restarted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/inspect_container', methods=['GET'])
def inspect_container():
    name = request.args.get('name')
    if not name:
        return jsonify({"status": "error", "message": "Missing container name"}), 400
    try:
        client = docker.from_env()
        container = client.containers.get(name)
        info = container.attrs
        return jsonify({"status": "success", "info": info})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/iptables_rule', methods=['POST'])
def iptables_rule():
    data = request.get_json()
    action = data.get('action')  # 'add' or 'remove'
    port = str(data.get('port'))
    protocol = data.get('protocol', 'tcp')
    if action not in ['add', 'remove'] or not port:
        return jsonify({"status": "error", "message": "Missing or invalid action/port"}), 400
    try:
        if action == 'add':
            cmd = ["sudo", "iptables", "-A", "INPUT", "-p", protocol, "--dport", port, "-j", "ACCEPT"]
        else:
            cmd = ["sudo", "iptables", "-D", "INPUT", "-p", protocol, "--dport", port, "-j", "ACCEPT"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return jsonify({"status": "success", "message": f"Rule {action}ed for port {port}/{protocol}"})
        else:
            return jsonify({"status": "error", "message": result.stderr}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082)
