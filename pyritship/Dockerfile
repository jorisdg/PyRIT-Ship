FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . .

# All env vars are optional; pass via docker run -e or --env-file
ENV OPENAI_CHAT_MODEL_NAME="" \
    OPENAI_CHAT_ENDPOINT="" \
    OPENAI_CHAT_KEY="" \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5001 \
    FLASK_DEBUG=false \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8001

EXPOSE 5001 8001

# NOTE: InteractiveBrowserCredential will NOT work in a headless container.
# So make sure to provide OPENAI_CHAT_KEY
# Change the command to run mcp_server.py if you want to run the MCP server instead of the Flask app.
CMD ["/app/venv/bin/python3", "restapi_server.py"]
#CMD ["/app/venv/bin/python3", "mcp_server.py"]
