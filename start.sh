#!/bin/bash
# Script de démarrage pour Railway
PORT=${PORT:-8000}
exec uvicorn mcp_server:app --host 0.0.0.0 --port $PORT
