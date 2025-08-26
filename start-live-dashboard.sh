#!/bin/bash

# GitHub Events Monitor - Live Dashboard Startup Script
# This script starts the API server and opens the dashboard

set -e

echo "🚀 GitHub Events Monitor - Live Dashboard"
echo "======================================="

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.11+ first."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  WARNING: GITHUB_TOKEN not set. API rate limits will be lower."
    echo "   To set it: export GITHUB_TOKEN=your_personal_access_token"
    echo ""
fi

# Initialize database
echo "🗄️  Initializing database..."
python -c "
import asyncio
from src.github_events_monitor.collector import GitHubEventsCollector

async def init():
    collector = GitHubEventsCollector('github_events.db')
    await collector.initialize_database()
    print('✅ Database initialized')

asyncio.run(init())
"

# Collect initial data
echo "📡 Collecting initial GitHub Events data..."
python -c "
import asyncio
from src.github_events_monitor.collector import GitHubEventsCollector

async def collect():
    collector = GitHubEventsCollector('github_events.db')
    await collector.initialize_database()
    count = await collector.collect_and_store(limit=100)
    print(f'✅ Collected {count} initial events')

asyncio.run(collect())
"

# Function to kill background processes on script exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start API server
echo "🌐 Starting API server..."
export CORS_ORIGINS="*"
python -m src.github_events_monitor.api &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API server to start..."
sleep 3

# Test API connection
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API server is running at http://localhost:8000"
else
    echo "❌ Failed to start API server"
    exit 1
fi

# Open dashboard in browser (if available)
DASHBOARD_URL="file://$(pwd)/docs/index.html"
echo "📊 Dashboard available at: $DASHBOARD_URL"
echo ""

# Try to open dashboard in browser
if command -v xdg-open &> /dev/null; then
    echo "🌐 Opening dashboard in browser..."
    xdg-open "$DASHBOARD_URL" &
elif command -v open &> /dev/null; then
    echo "🌐 Opening dashboard in browser..."
    open "$DASHBOARD_URL" &
else
    echo "💡 Manually open the dashboard at: $DASHBOARD_URL"
fi

echo ""
echo "🎯 Live Dashboard Instructions:"
echo "   - Dashboard will automatically connect to http://localhost:8000"
echo "   - Data refreshes every 30 seconds"
echo "   - Use 'Test Connection' button to verify API connectivity"
echo "   - Press Ctrl+C to stop the server"
echo ""
echo "📈 API Endpoints:"
echo "   - Health: http://localhost:8000/health"
echo "   - Docs: http://localhost:8000/docs"
echo "   - Event Counts: http://localhost:8000/metrics/event-counts?offset_minutes=60"
echo "   - Trending: http://localhost:8000/metrics/trending"
echo ""

# Keep script running and show logs
echo "📊 Live dashboard running... (Press Ctrl+C to stop)"
echo "---------------------------------------------------"

# Follow API logs
wait $API_PID
