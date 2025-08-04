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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082)
    