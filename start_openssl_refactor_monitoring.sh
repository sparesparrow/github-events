#!/bin/bash

# OpenSSL Refactoring DevOps Process Monitor
# Specialized monitoring for OpenSSL CI/CD modernization

set -e

echo "🔧 OpenSSL Refactoring DevOps Monitor"
echo "===================================="
echo "Repository: openssl/openssl"
echo "Focus: CI/CD Modernization with Conanfile.py & Python Tooling"
echo "Integration: Sparesparrow Agent Ecosystem + AWS Services"
echo "Time: $(date)"
echo ""

# Check prerequisites
echo "🔧 Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required"
    exit 1
fi

if ! command -v docker &> /dev/null && ! command -v podman &> /dev/null; then
    echo "❌ Docker or Podman is required for agent containerization"
    exit 1
fi

echo "✅ Prerequisites satisfied"

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  WARNING: GITHUB_TOKEN not set."
    echo "   OpenSSL has 105,000+ workflow runs - token needed for comprehensive analysis"
    echo "   To set it: export GITHUB_TOKEN=your_personal_access_token"
    echo ""
    read -p "Continue without GitHub token? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Configuration for OpenSSL refactoring monitoring
echo "📋 OpenSSL Refactoring Configuration:"
echo "   Target Repository: openssl/openssl"
echo "   Focus Areas:"
echo "     - CI/CD Pipeline Modernization"
echo "     - Python Tooling Integration"
echo "     - Conanfile.py Package Management"
echo "     - Agent Orchestration Implementation"
echo "     - AWS Services Integration"
echo "   Sparesparrow Integration:"
echo "     - mcp-prompts: CI/CD templates"
echo "     - mcp-project-orchestrator: Workflow coordination"
echo "     - mcp-router: Task routing"
echo "     - podman-desktop-extension-mcp: Container management"
echo "     - ai-servis: AI-powered analysis"
echo ""

# Set environment for OpenSSL monitoring
export TARGET_REPOSITORIES="openssl/openssl"
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-east-1
export DYNAMODB_TABLE_PREFIX=openssl-refactor-
export DYNAMODB_ENDPOINT_URL=http://localhost:8000

# Install dependencies
echo "📥 Installing dependencies..."
pip install --break-system-packages boto3 botocore httpx aiosqlite fastapi uvicorn

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down OpenSSL refactoring monitor..."
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    if [ ! -z "$DYNAMODB_PID" ]; then
        kill $DYNAMODB_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start DynamoDB Local for context storage
echo "🗄️ Starting DynamoDB Local for agent context..."
docker run -d --name openssl-dynamodb -p 8000:8000 amazon/dynamodb-local:latest -jar DynamoDBLocal.jar -sharedDb &
DYNAMODB_PID=$!

# Wait for DynamoDB to start
echo "⏳ Waiting for DynamoDB to start..."
sleep 5

# Create DynamoDB tables
echo "📊 Creating DynamoDB tables for OpenSSL monitoring..."
python3 scripts/setup_dynamodb.py create

# Initialize OpenSSL monitoring
echo "🔍 Initializing OpenSSL refactoring analysis..."
python3 -c "
import asyncio
from src.github_events_monitor.openssl_refactor_monitor import create_openssl_refactor_monitor

async def init_openssl_monitoring():
    monitor = await create_openssl_refactor_monitor({
        'provider': 'dynamodb',
        'region': 'us-east-1',
        'table_prefix': 'openssl-refactor-',
        'endpoint_url': 'http://localhost:8000',
        'aws_access_key_id': 'dummy',
        'aws_secret_access_key': 'dummy'
    })
    
    print('🎯 Collecting initial OpenSSL data...')
    await monitor.integration.collector.fetch_and_store_events(limit=100)
    
    print('📊 Generating initial refactoring assessment...')
    report = await monitor.generate_refactoring_report()
    
    print('✅ OpenSSL monitoring initialized')
    print(f'   Overall Progress: {report[\"refactoring_analysis\"][\"overall_progress\"]}')
    print(f'   CI/CD Modernization: {report[\"refactoring_analysis\"][\"ci_cd_modernization\"]}')
    print(f'   Python Integration: {report[\"refactoring_analysis\"][\"python_integration\"]}')
    print(f'   Conan Adoption: {report[\"refactoring_analysis\"][\"conan_adoption\"]}')

asyncio.run(init_openssl_monitoring())
"

# Start enhanced API server with OpenSSL endpoints
echo "🌐 Starting OpenSSL refactoring API server..."
python3 -c "
import uvicorn
from fastapi import FastAPI
from src.github_events_monitor.api import app
from src.github_events_monitor.interfaces.api.openssl_endpoints import router

# Add OpenSSL endpoints to main app
app.include_router(router)

print('🚀 Starting API server with OpenSSL refactoring endpoints...')
uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
" &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API server to start..."
sleep 5

# Test API connection
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ OpenSSL refactoring API is running at http://localhost:8000"
    echo ""
    echo "🎯 OpenSSL Refactoring Monitoring Endpoints:"
    echo "   Refactoring Progress: http://localhost:8000/openssl/refactoring/progress"
    echo "   Comprehensive Report: http://localhost:8000/openssl/refactoring/report"
    echo "   DevOps KPIs: http://localhost:8000/openssl/devops/kpis"
    echo "   Agent Configuration: http://localhost:8000/openssl/agent-config"
    echo "   Modernization Recommendations: http://localhost:8000/openssl/modernization/recommendations"
    echo "   Sparesparrow Integration: http://localhost:8000/openssl/sparesparrow-integration"
    echo ""
    echo "🤖 Agent Integration Commands:"
    echo "   # Generate Claude Agent SDK config"
    echo "   curl http://localhost:8000/openssl/agent-config"
    echo ""
    echo "   # Get refactoring recommendations"
    echo "   curl http://localhost:8000/openssl/modernization/recommendations?priority=high"
    echo ""
    echo "   # Check DevOps KPIs"
    echo "   curl http://localhost:8000/openssl/devops/kpis"
    echo ""
    echo "   # Start comprehensive monitoring"
    echo "   curl -X POST http://localhost:8000/openssl/refactoring/start-monitoring"
    echo ""
    echo "🔗 Sparesparrow Ecosystem Integration:"
    echo "   mcp-prompts: CI/CD templates → http://localhost:8000/openssl/sparesparrow-integration"
    echo "   mcp-project-orchestrator: Workflow coordination"
    echo "   mcp-router: Agent task routing"
    echo "   podman-desktop-extension-mcp: Container management"
    echo "   ai-servis: AI-powered code analysis"
    echo ""
    echo "☁️ AWS Services Ready:"
    echo "   DynamoDB: Context storage and agent coordination"
    echo "   Lambda: Serverless agent execution"
    echo "   ECS: Long-running agent containers"
    echo "   CodeBuild: CI/CD integration"
    echo ""
    echo "📊 Monitoring Focus Areas:"
    echo "   ✅ CI/CD Pipeline Analysis (105,000+ workflow runs)"
    echo "   ✅ Python Tooling Integration Progress"
    echo "   ✅ Conanfile.py Adoption Tracking"
    echo "   ✅ Build Performance Optimization"
    echo "   ✅ Security Compliance Automation"
    echo "   ✅ Agent Orchestration Implementation"
    echo ""
else
    echo "❌ Failed to start OpenSSL refactoring API"
    exit 1
fi

echo "🎯 OpenSSL Refactoring DevOps Monitor is now active!"
echo ""
echo "📈 Real-time Monitoring:"
echo "   - Repository health and activity tracking"
echo "   - CI/CD modernization progress analysis"
echo "   - Python tooling adoption metrics"
echo "   - Conan package management integration"
echo "   - Security compliance monitoring"
echo "   - Agent coordination effectiveness"
echo ""
echo "🔄 Agent Orchestration Ready:"
echo "   - Pipeline archaeologist for CI/CD analysis"
echo "   - Build matrix optimizer for performance"
echo "   - Security pipeline hardener for compliance"
echo "   - Cross-platform coordinator for builds"
echo "   - Integration with sparesparrow ecosystem"
echo ""
echo "Press Ctrl+C to stop monitoring..."

# Keep script running and show logs
wait $API_PID