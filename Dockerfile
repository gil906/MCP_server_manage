FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mcp_server_script.py .
# Create docker group and appuser with UID 1000, add to docker group
RUN groupadd -g 986 docker && useradd -u 1000 -g 986 -m appuser && usermod -aG docker appuser
EXPOSE 8082
USER appuser
CMD ["python", "mcp_server_script.py"]
