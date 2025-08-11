FROM python:3.11-slim

# Install tooling used by some actions (ping/ip/iptables optional but useful)
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 iputils-ping iptables curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY mcp_server_script.py .

# Create docker group and appuser with UID 1000, add to docker group
RUN groupadd -g 986 docker || true \
 && useradd -u 1000 -g 986 -m appuser || true \
 && usermod -aG docker appuser || true

EXPOSE 8082
USER appuser

# Run FastMCP server via the Python script (which uses FastMCP). No Flask.
CMD ["python", "mcp_server_script.py"]
