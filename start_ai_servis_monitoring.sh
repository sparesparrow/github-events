#!/bin/bash

# AI-Servis Repository Monitoring Startup Script
# Focused monitoring for sparesparrow/ai-servis repository

set -e

echo "🎯 AI-Servis Repository Monitor"
echo "==============================="
echo "Repository: sparesparrow/ai-servis"
echo "Time: $(date)"
echo ""

# Check if Python is available
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo "🐍 Using Python: $PYTHON_CMD"

# Load AI-Servis specific configuration
if [ -f ".env.ai-servis" ]; then
    echo "📋 Loading AI-Servis configuration..."
    export $(grep -v '^#' .env.ai-servis | xargs)
else
    echo "⚠️ No .env.ai-servis file found, using defaults..."
    export TARGET_REPOSITORIES="sparesparrow/ai-servis"
    export DATABASE_PROVIDER="sqlite"
    export DATABASE_PATH="./ai_servis_events.db"
    export POLL_INTERVAL="180"
fi

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  WARNING: GITHUB_TOKEN not set. API rate limits will be lower."
    echo "   To set it: export GITHUB_TOKEN=your_personal_access_token"
    echo "   Or add it to .env.ai-servis file"
    echo ""
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
fi

echo "🔄 Activating virtual environment..."
source .venv/bin/activate

echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Initialize database
echo "🗄️ Initializing database for AI-Servis monitoring..."
$PYTHON_CMD -c "
import asyncio
from src.github_events_monitor.enhanced_event_collector import create_enhanced_collector

async def init():
    collector = create_enhanced_collector(target_repositories=['sparesparrow/ai-servis'])
    await collector.initialize()
    print('✅ Database initialized for AI-Servis monitoring')

asyncio.run(init())
"

# Run focused monitoring
echo "🎯 Starting AI-Servis focused monitoring..."
$PYTHON_CMD monitor_ai_servis.py

echo ""
echo "🌐 Starting API server for AI-Servis monitoring..."
export CORS_ORIGINS="*"
$PYTHON_CMD -m src.github_events_monitor.api &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API server to start..."
sleep 3

# Test API connection
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API server is running at http://localhost:8000"
    echo ""
    echo "🎯 AI-Servis Monitoring Endpoints:"
    echo "   Repository Health: http://localhost:8000/metrics/repository-health?repo=sparesparrow/ai-servis"
    echo "   Recent Commits: http://localhost:8000/commits/recent?repo=sparesparrow/ai-servis&hours=24"
    echo "   Change Summary: http://localhost:8000/commits/summary?repo=sparesparrow/ai-servis&hours=168"
    echo "   Security Report: http://localhost:8000/metrics/security-monitoring?repo=sparesparrow/ai-servis"
    echo "   Developer Metrics: http://localhost:8000/metrics/developer-productivity?repo=sparesparrow/ai-servis"
    echo "   Event Anomalies: http://localhost:8000/metrics/event-anomalies?repo=sparesparrow/ai-servis"
    echo ""
    echo "📊 Quick Commands:"
    echo "   curl \"http://localhost:8000/commits/recent?repo=sparesparrow/ai-servis&hours=24\""
    echo "   curl \"http://localhost:8000/metrics/repository-health?repo=sparesparrow/ai-servis\""
    echo "   curl \"http://localhost:8000/commits/summary?repo=sparesparrow/ai-servis&hours=168\""
    echo ""
else
    echo "❌ Failed to start API server"
    exit 1
fi

# Function to kill background processes on script exit
cleanup() {
    echo ""
    echo "🛑 Shutting down AI-Servis monitoring..."
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

echo "🎯 AI-Servis monitoring is now active!"
echo "   Repository: sparesparrow/ai-servis"
echo "   Polling interval: ${POLL_INTERVAL:-180} seconds"
echo "   Database: ${DATABASE_PATH:-./ai_servis_events.db}"
echo ""
echo "Press Ctrl+C to stop monitoring..."

# Keep script running
wait $API_PID