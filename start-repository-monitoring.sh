#!/bin/bash

# Repository Monitoring Startup Script
# Sets up complete monitoring of OpenSSL repository and comparison with your fork

set -e

echo "🚀 Starting Repository Comparison Monitoring System"
echo "=================================================="

# Configuration
PRIMARY_REPO="${PRIMARY_REPO:-openssl/openssl}"
COMPARISON_REPO="${COMPARISON_REPO:-sparesparrow/github-events}"
DATABASE_PATH="${DATABASE_PATH:-./github_events.db}"
API_PORT="${API_PORT:-8000}"
TIME_WINDOW="${TIME_WINDOW:-168}"

echo "📊 Configuration:"
echo "  Primary Repository: $PRIMARY_REPO"
echo "  Comparison Repository: $COMPARISON_REPO"
echo "  Database Path: $DATABASE_PATH"
echo "  API Port: $API_PORT"
echo "  Time Window: $TIME_WINDOW hours"
echo ""

# Check for required tools
echo "🔍 Checking dependencies..."
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed."; exit 1; }
command -v sqlite3 >/dev/null 2>&1 || { echo "❌ SQLite 3 is required but not installed."; exit 1; }

# Set up Python environment
echo "🐍 Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

source .venv/bin/activate
echo "✅ Virtual environment activated"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q -e .
echo "✅ Dependencies installed"

# Initialize database
echo "🗄️ Initializing database..."
mkdir -p database
if [ -f database/schema.sql ]; then
    sqlite3 "$DATABASE_PATH" < database/schema.sql 2>/dev/null || true
fi
echo "✅ Database initialized"

# Set environment variables
export TARGET_REPOSITORIES="$PRIMARY_REPO,$COMPARISON_REPO"
export PRIMARY_REPOSITORIES="$PRIMARY_REPO"
export COMPARISON_REPOSITORIES="$COMPARISON_REPO"
export DATABASE_PATH="$DATABASE_PATH"
export API_HOST="0.0.0.0"
export API_PORT="$API_PORT"
export CORS_ORIGINS="*"

echo "🔧 Environment configured"

# Collect initial data
echo "📡 Collecting initial data..."
python -c "
import asyncio
import os
from src.github_events_monitor.event_collector import GitHubEventsCollector

async def main():
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print('⚠️ GITHUB_TOKEN not set - using anonymous requests (limited rate)')
    
    collector = GitHubEventsCollector('$DATABASE_PATH', token)
    await collector.initialize_database()
    
    repos = ['$PRIMARY_REPO', '$COMPARISON_REPO']
    total_collected = 0
    
    for repo in repos:
        print(f'📊 Collecting events for {repo}...')
        try:
            n = await collector.collect_repository_events(repo, limit=100)
            total_collected += n
            print(f'✅ Collected {n} events for {repo}')
        except Exception as e:
            print(f'⚠️ Error collecting events for {repo}: {e}')
    
    print(f'📈 Total events collected: {total_collected}')

asyncio.run(main())
"

# Start API server
echo "🌐 Starting API server..."
python -m src.github_events_monitor.api > api.log 2>&1 &
API_PID=$!
echo $API_PID > api.pid

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
for i in {1..30}; do
    if curl -fsS http://localhost:$API_PORT/health >/dev/null 2>&1; then
        echo "✅ API server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API server failed to start"
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
    sleep 2
done

# Test comparison endpoint
echo "🧪 Testing repository comparison..."
COMPARISON_URL="http://localhost:$API_PORT/comparison/repositories?primary_repo=$PRIMARY_REPO&comparison_repo=$COMPARISON_REPO&hours=$TIME_WINDOW"
if curl -fsS "$COMPARISON_URL" >/dev/null 2>&1; then
    echo "✅ Repository comparison endpoint working"
else
    echo "⚠️ Repository comparison endpoint not responding"
fi

# Generate initial comparison report
echo "📋 Generating initial comparison report..."
mkdir -p reports
python -c "
import json
import requests
import os
from datetime import datetime

try:
    url = 'http://localhost:$API_PORT/comparison/repositories'
    params = {
        'primary_repo': '$PRIMARY_REPO',
        'comparison_repo': '$COMPARISON_REPO', 
        'hours': $TIME_WINDOW
    }
    
    response = requests.get(url, params=params, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        
        # Save detailed report
        with open('reports/initial_comparison.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        # Create summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'primary_repo': '$PRIMARY_REPO',
            'comparison_repo': '$COMPARISON_REPO',
            'primary_events': data['metrics']['primary']['total_events'],
            'comparison_events': data['metrics']['comparison']['total_events'],
            'recommendations_count': len(data['recommendations'])
        }
        
        with open('reports/summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print('✅ Initial comparison report generated')
        print(f'📊 Primary repo events: {summary[\"primary_events\"]}')
        print(f'📊 Comparison repo events: {summary[\"comparison_events\"]}')
        print(f'💡 Recommendations: {summary[\"recommendations_count\"]}')
        
    else:
        print(f'⚠️ Failed to generate report: {response.status_code}')
        
except Exception as e:
    print(f'⚠️ Error generating report: {e}')
"

# Update dashboard data
echo "📊 Updating dashboard data..."
if [ -f reports/summary.json ]; then
    cp reports/summary.json docs/comparison_data.json
    echo "✅ Dashboard data updated"
fi

echo ""
echo "🎉 Repository Monitoring System Started Successfully!"
echo "=================================================="
echo ""
echo "📊 Available Endpoints:"
echo "  Health Check: http://localhost:$API_PORT/health"
echo "  Repository Comparison: http://localhost:$API_PORT/comparison/repositories"
echo "  Detailed Metrics: http://localhost:$API_PORT/metrics/repository-detailed"
echo "  CI Analysis: http://localhost:$API_PORT/analysis/ci-automation"
echo "  Dashboard Data: http://localhost:$API_PORT/dashboard/comparison"
echo ""
echo "🌐 Dashboards:"
echo "  Main Dashboard: http://localhost:$API_PORT/docs"
echo "  Comparison Dashboard: file://$(pwd)/docs/repository_comparison.html"
echo ""
echo "📋 Reports:"
echo "  Initial Report: reports/initial_comparison.json"
echo "  Summary: reports/summary.json"
echo ""
echo "🔧 Management:"
echo "  Stop server: kill \$(cat api.pid)"
echo "  View logs: tail -f api.log"
echo "  Database: $DATABASE_PATH"
echo ""
echo "💡 Next Steps:"
echo "  1. Open the comparison dashboard in your browser"
echo "  2. Set GITHUB_TOKEN environment variable for higher rate limits"
echo "  3. Configure automated monitoring with the GitHub workflow"
echo ""
echo "🚀 Happy monitoring!"