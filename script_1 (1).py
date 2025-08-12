# Create supporting configuration files

# 1. Requirements file
requirements_txt = '''# GitHub Events MCP Server Dependencies

# Core MCP dependencies
mcp[cli]>=1.4.1

# HTTP client for GitHub API
httpx>=0.28.1

# Async PostgreSQL driver
asyncpg>=0.29.0

# Web framework
fastapi>=0.104.1
uvicorn[standard]>=0.24.0

# Data validation
pydantic>=2.5.0

# Visualization
matplotlib>=3.8.0

# Environment management
python-dotenv>=1.0.0

# Additional utilities
aiofiles>=23.2.1
'''

# 2. Environment configuration template
env_template = '''# GitHub Events MCP Server Configuration

# GitHub API Token (optional but recommended for higher rate limits)
GITHUB_TOKEN=your_github_token_here

# Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/github_events

# Polling configuration
POLL_INTERVAL=30

# Logging level
LOG_LEVEL=INFO

# Server configuration
MCP_TRANSPORT_TYPE=stdio
HOST=0.0.0.0
PORT=8000
'''

# 3. Docker Compose configuration
docker_compose = '''version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: github_events_user
      POSTGRES_PASSWORD: github_events_pass
      POSTGRES_DB: github_events
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U github_events_user -d github_events"]
      interval: 10s
      timeout: 5s
      retries: 5

  mcp-server:
    build: .
    environment:
      - DATABASE_URL=postgresql://github_events_user:github_events_pass@postgres:5432/github_events
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - POLL_INTERVAL=30
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs

volumes:
  postgres_data:
'''

# 4. Dockerfile
dockerfile = '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD python -c "import asyncio; import sys; sys.exit(0)"

# Run the application
CMD ["python", "github_events_mcp_server.py"]
'''

# 5. Database initialization script
init_sql = '''-- GitHub Events MCP Server Database Schema

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create events table with proper indexing
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    gh_id TEXT UNIQUE NOT NULL,
    repo_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    payload JSONB,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_repo_created 
    ON events (repo_name, created_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_events_type_created 
    ON events (event_type, created_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_events_created_at 
    ON events (created_at DESC);

-- Create aggregates table for fast metric queries
CREATE TABLE IF NOT EXISTS event_aggregates (
    id BIGSERIAL PRIMARY KEY,
    repo_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    minute_bucket TIMESTAMPTZ NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repo_name, event_type, minute_bucket)
);

-- Index for aggregates table
CREATE INDEX IF NOT EXISTS idx_aggregates_repo_type_minute 
    ON event_aggregates (repo_name, event_type, minute_bucket DESC);

-- Create a view for recent activity summary
CREATE OR REPLACE VIEW recent_activity AS
SELECT 
    repo_name,
    event_type,
    COUNT(*) as event_count,
    MIN(created_at) as first_event,
    MAX(created_at) as last_event,
    MAX(created_at) - MIN(created_at) as time_span
FROM events 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY repo_name, event_type
ORDER BY event_count DESC;

-- Create function to calculate PR intervals
CREATE OR REPLACE FUNCTION calculate_pr_interval(repo_name_param TEXT)
RETURNS TABLE(
    pr_count BIGINT,
    avg_interval_seconds NUMERIC,
    median_interval_seconds NUMERIC,
    stddev_interval_seconds NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH pr_events AS (
        SELECT 
            created_at,
            LAG(created_at) OVER (ORDER BY created_at) as prev_created_at
        FROM events 
        WHERE repo_name = repo_name_param 
          AND event_type = 'PullRequestEvent'
          AND payload->>'action' = 'opened'
        ORDER BY created_at
    ),
    intervals AS (
        SELECT EXTRACT(EPOCH FROM (created_at - prev_created_at)) as interval_seconds
        FROM pr_events 
        WHERE prev_created_at IS NOT NULL
    )
    SELECT 
        (SELECT COUNT(*) FROM pr_events)::BIGINT as pr_count,
        AVG(interval_seconds)::NUMERIC as avg_interval_seconds,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY interval_seconds)::NUMERIC as median_interval_seconds,
        STDDEV(interval_seconds)::NUMERIC as stddev_interval_seconds
    FROM intervals;
END;
$$ LANGUAGE plpgsql;

-- Insert sample data for testing (optional)
-- This would typically be populated by the MCP server
'''

# 6. MCP Client configuration for Claude Desktop
claude_config = '''{
  "mcpServers": {
    "github-events-monitor": {
      "command": "python",
      "args": [
        "/absolute/path/to/github_events_mcp_server.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://github_events_user:github_events_pass@localhost:5432/github_events",
        "GITHUB_TOKEN": "your_github_token_here",
        "POLL_INTERVAL": "30"
      }
    }
  }
}'''

# 7. Development startup script
startup_script = '''#!/bin/bash
# GitHub Events MCP Server Development Setup

set -e

echo "🚀 Setting up GitHub Events MCP Server..."

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)
required_version="3.11"

if [ "$(printf '%s\\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
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
'''

# Save all files
files_to_create = {
    "requirements.txt": requirements_txt,
    ".env.template": env_template,
    "docker-compose.yml": docker_compose,
    "Dockerfile": dockerfile,
    "init.sql": init_sql,
    "claude_desktop_config.json": claude_config,
    "setup.sh": startup_script
}

created_files = []
for filename, content in files_to_create.items():
    with open(filename, "w") as f:
        f.write(content)
    created_files.append(filename)

print("✅ Created supporting configuration files:")
for filename in created_files:
    print(f"   📄 {filename}")

# Make setup script executable
import os
os.chmod("setup.sh", 0o755)
print("🔧 Made setup.sh executable")