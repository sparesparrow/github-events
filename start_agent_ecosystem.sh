#!/bin/bash

# Sparesparrow Agent Ecosystem Startup Script
# Orchestrates multi-repository monitoring with containerized agents

set -e

echo "🌟 Sparesparrow Agent Ecosystem"
echo "=============================="
echo "Multi-Repository Orchestration with GitHub Events Context"
echo "Time: $(date)"
echo ""

# Check required tools
echo "🔧 Checking prerequisites..."

if ! command -v docker &> /dev/null && ! command -v podman &> /dev/null; then
    echo "❌ Docker or Podman is required for agent containerization"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is required for orchestration"
    exit 1
fi

echo "✅ Prerequisites satisfied"

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  WARNING: GITHUB_TOKEN not set. Agent coordination will have limited GitHub API access."
    echo "   To set it: export GITHUB_TOKEN=your_personal_access_token"
    echo ""
    read -p "Continue without GitHub token? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Setup environment
echo "🔧 Setting up agent ecosystem environment..."

# Create necessary directories
mkdir -p logs
mkdir -p data/agent-context
mkdir -p .claude/agents

# Set environment variables for agent coordination
export TARGET_REPOSITORIES="sparesparrow/mcp-prompts,sparesparrow/mcp-project-orchestrator,sparesparrow/mcp-router,sparesparrow/podman-desktop-extension-mcp,sparesparrow/ai-servis"
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-east-1
export DYNAMODB_TABLE_PREFIX=agents-github-events-
export DYNAMODB_ENDPOINT_URL=http://localhost:8000

echo "📋 Agent Ecosystem Configuration:"
echo "   Repositories: $TARGET_REPOSITORIES"
echo "   Database: DynamoDB (local)"
echo "   Agent Containers: 5 specialized agents"
echo "   Coordination: Multi-repo orchestrator"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down agent ecosystem..."
    docker-compose -f docker-compose.agents.yml down
    echo "✅ Agent ecosystem shutdown completed"
    exit 0
}

# Set up cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start the agent ecosystem
echo "🚀 Starting agent ecosystem..."
echo "This will start:"
echo "   - DynamoDB Local (context storage)"
echo "   - GitHub Events API (context provider)"
echo "   - 5 Specialized Repository Agents"
echo "   - Agent Coordination Dashboard"
echo "   - GitHub Events MCP Server"
echo ""

# Build and start services
echo "📦 Building agent containers..."
docker-compose -f docker-compose.agents.yml build

echo "🔄 Starting agent ecosystem services..."
docker-compose -f docker-compose.agents.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

services=(
    "http://localhost:8000:DynamoDB Local"
    "http://localhost:8080/health:GitHub Events API"
    "http://localhost:8081/health:Agent Dashboard"
)

all_healthy=true

for service in "${services[@]}"; do
    IFS=':' read -r url name <<< "$service"
    if curl -s -f "$url" > /dev/null; then
        echo "   ✅ $name - Healthy"
    else
        echo "   ❌ $name - Not responding"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    echo ""
    echo "🎉 Agent Ecosystem Successfully Started!"
    echo ""
    echo "🌐 Access Points:"
    echo "   Agent Dashboard: http://localhost:8081"
    echo "   GitHub Events API: http://localhost:8080"
    echo "   DynamoDB Local: http://localhost:8000"
    echo ""
    echo "🎯 Repository Monitoring:"
    echo "   mcp-prompts: http://localhost:8081/api/repository/sparesparrow/mcp-prompts"
    echo "   mcp-project-orchestrator: http://localhost:8081/api/repository/sparesparrow/mcp-project-orchestrator"
    echo "   mcp-router: http://localhost:8081/api/repository/sparesparrow/mcp-router"
    echo "   podman-desktop-extension-mcp: http://localhost:8081/api/repository/sparesparrow/podman-desktop-extension-mcp"
    echo "   ai-servis: http://localhost:8081/api/repository/sparesparrow/ai-servis"
    echo ""
    echo "🤖 Agent Integration:"
    echo "   MCP Server: Connected (stdio)"
    echo "   Agent Tools: get_repository_context, get_multi_repository_context, etc."
    echo "   Context Management: Active with token optimization"
    echo ""
    echo "📊 Quick Commands:"
    echo "   # Get ecosystem summary"
    echo "   curl http://localhost:8081/api/ecosystem/summary"
    echo ""
    echo "   # Get specific repository context"
    echo "   curl http://localhost:8080/metrics/repository-health?repo=sparesparrow/ai-servis"
    echo ""
    echo "   # Get deployment readiness"
    echo "   curl http://localhost:8080/metrics/release-deployment?repo=sparesparrow/mcp-router"
    echo ""
    echo "🔄 Agent Status:"
    docker-compose -f docker-compose.agents.yml ps
    echo ""
    echo "📋 To use with Claude Agent SDK:"
    echo "   1. Configure MCP server: python scripts/github_events_mcp_server.py"
    echo "   2. Use agents configuration from examples/sparesparrow_agent_config.js"
    echo "   3. Access agent coordination via dashboard or API"
    echo ""
    echo "Press Ctrl+C to stop the agent ecosystem..."
    
    # Show live logs from all agents
    echo "📄 Live Agent Logs (Ctrl+C to stop):"
    docker-compose -f docker-compose.agents.yml logs -f
else
    echo ""
    echo "❌ Some services failed to start. Check the logs:"
    docker-compose -f docker-compose.agents.yml logs
    exit 1
fi