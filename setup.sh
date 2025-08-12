#!/bin/bash
# GitHub Events MCP Server Development Setup

set -e

echo "🚀 Setting up GitHub Events MCP Server..."

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists, if not copy from template
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.template .env
    echo "🔑 Please edit .env file with your configuration"
fi

# Start PostgreSQL with Docker Compose if not running
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "🐘 Starting PostgreSQL..."
    docker-compose up -d postgres
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 10
fi

# Run database migrations
echo "🗄️ Setting up database..."
export $(cat .env | xargs)
python3 -c "
import asyncio
import asyncpg
import os

async def setup_db():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    with open('init.sql', 'r') as f:
        await conn.execute(f.read())
    await conn.close()
    print('✅ Database setup complete')

asyncio.run(setup_db())
"

echo "🎉 Setup complete!"
echo ""
echo "To start the MCP server:"
echo "  python github_events_mcp_server.py"
echo ""
echo "To test with MCP Inspector:"
echo "  mcp dev github_events_mcp_server.py"
echo ""
echo "To use with Claude Desktop:"
echo "  1. Copy claude_desktop_config.json content to your Claude config"
echo "  2. Update the absolute path in the config"
echo "  3. Restart Claude Desktop"
