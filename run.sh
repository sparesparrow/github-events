#!/bin/bash
# GitHub Events Monitor - Quick Run Script

set -e

echo "🚀 GitHub Events Monitor Setup and Run"
echo "======================================"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.template .env
    echo "🔑 Please edit .env file with your GitHub token"
    echo "   You can get a token from: https://github.com/settings/tokens"
    echo ""
fi

# Ask user what to run
echo "What would you like to run?"
echo "1) FastAPI REST API server (http://localhost:8000)"
echo "2) MCP server (for Claude Desktop integration)"  
echo "3) Run tests"
echo "4) Check system status"

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🌐 Starting FastAPI server..."
        echo "📖 API docs will be available at: http://localhost:8000/docs"
        python main_api.py
        ;;
    2)
        echo "🔌 Starting MCP server..."
        echo "💡 Use this with Claude Desktop or other MCP clients"
        python main_mcp.py
        ;;
    3)
        echo "🧪 Running tests..."
        pytest -v
        ;;
    4)
        echo "📊 System Status Check"
        echo "====================="
        python -c "
import os
from github_events_monitor.config import config

print(f'Database path: {config.get_database_path()}')
print(f'GitHub token configured: {"Yes" if config.github_token else "No"}')
print(f'Poll interval: {config.poll_interval_seconds} seconds')

if os.path.exists(config.get_database_path()):
    import sqlite3
    conn = sqlite3.connect(config.get_database_path())
    cursor = conn.execute('SELECT COUNT(*) FROM events')
    count = cursor.fetchone()[0]
    print(f'Events in database: {count:,}')
    conn.close()
else:
    print('Database: Not created yet')
"
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac
