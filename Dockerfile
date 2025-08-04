# To build: docker-compose -f mcpserver.yml up -d --build


FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mcp_server_script.py .
EXPOSE 8082
CMD ["python", "mcp_server_script.py"]
