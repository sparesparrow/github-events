#!/bin/bash

# GitHub Events Monitor - Docker Entrypoint
# This script starts the appropriate service based on environment variables

set -e

echo "🚀 Starting GitHub Events Monitor..."

# Set default values
API_HOST=${API_HOST:-"0.0.0.0"}
API_PORT=${API_PORT:-"8000"}
DATABASE_PATH=${DATABASE_PATH:-"/app/data/github_events.db"}
POLL_INTERVAL=${POLL_INTERVAL:-"300"}

# Ensure database directory exists
mkdir -p "$(dirname "$DATABASE_PATH")"

echo "📊 Configuration:"
echo "  - API Host: $API_HOST"
echo "  - API Port: $API_PORT"
echo "  - Database: $DATABASE_PATH"
echo "  - Poll Interval: ${POLL_INTERVAL}s"
echo "  - GitHub Token: ${GITHUB_TOKEN:+'Configured'}"
echo ""

# Check if we should run MCP server or REST API
if [ "$MCP_MODE" = "true" ]; then
    echo "🤖 Starting MCP Server..."
    if [ -f "scripts/mcp_server.py" ]; then
        exec python scripts/mcp_server.py
    else
        exec python -m github_events_monitor.mcp_server
    fi
else
    echo "🌐 Starting REST API Server..."
    exec python -m github_events_monitor.api
fi
