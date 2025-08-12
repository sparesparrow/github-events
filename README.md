# GitHub Events MCP Server

A comprehensive **Model Context Protocol (MCP) server** that monitors GitHub Events API for specific event types (WatchEvent, PullRequestEvent, IssuesEvent) and provides real-time metrics and insights through MCP tools, resources, and prompts.

## 🎯 Overview

This MCP server addresses the GitHub Events monitoring assignment by implementing a production-ready solution that:

- **Streams GitHub Events**: Continuously polls the GitHub Events API with proper rate limiting
- **Filters Relevant Events**: Focuses on WatchEvent, PullRequestEvent, and IssuesEvent
- **Provides Metrics**: Calculates average PR intervals and event counts via MCP tools
- **Offers Insights**: Exposes rich data through MCP resources and intelligent prompts
- **Ensures Reliability**: Implements proper error handling, caching, and database persistence

## 🏗️ Architecture

![System Context Diagram](github_events_mcp_context_diagram.png)

### MCP Implementation Design

Following MCP best practices, this server implements:

- **Prompts** (User-controlled): Templates for analysis and monitoring configuration
- **Resources** (Application-controlled): Real-time server status and recent event data  
- **Tools** (Model-controlled): Functions for metric calculation and data retrieval

### Key Components

1. **GitHub Events Poller**: Handles API polling with ETags and rate limiting
2. **Database Manager**: Manages PostgreSQL storage and metric calculations
3. **MCP Server**: Exposes functionality through the Model Context Protocol
4. **Background Tasks**: Continuous event ingestion and processing

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (recommended)
- **PostgreSQL 15+** (or use Docker)
- **GitHub Token** (optional, but recommended for higher rate limits)

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone and setup
git clone <your-repo>
cd github-events-mcp-server

# 2. Configure environment
cp .env.template .env
# Edit .env with your GITHUB_TOKEN

# 3. Start with Docker
docker-compose up --build

# 4. The MCP server will be running and polling GitHub Events!
```

### Option 2: Local Development

```bash
# 1. Run the automated setup
./setup.sh

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Start the MCP server
python github_events_mcp_server.py
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | "" (anonymous) |
| `DATABASE_URL` | PostgreSQL connection string | localhost:5432 |
| `POLL_INTERVAL` | Polling interval in seconds | 30 |
| `LOG_LEVEL` | Logging level | INFO |

### GitHub Token Setup

1. Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. Generate a token with `public_repo` scope (for public data access)
3. Add to your `.env` file: `GITHUB_TOKEN=ghp_your_token_here`

## 🛠️ MCP Integration

### With Claude Desktop

1. Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "github-events-monitor": {
      "command": "python",
      "args": ["/absolute/path/to/github_events_mcp_server.py"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/github_events",
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

2. Restart Claude Desktop
3. Look for the MCP tools icon (🔌) in the chat interface

### With Cursor

1. Configure Cursor's MCP settings to point to your server
2. Use the MCP tools in your development workflow

### Testing with MCP Inspector

```bash
# Install MCP CLI tools
npm install -g @modelcontextprotocol/inspector

# Start the inspector
mcp dev github_events_mcp_server.py

# Open http://localhost:3000 to interact with your server
```

## 📊 Available MCP Primitives

### Tools (Model-Controlled Functions)

#### `get_avg_pr_interval(repo: str)`
Calculate the average time between pull requests for a repository.

**Example**:
```
repo: "microsoft/vscode"
Returns: {
  "repo": "microsoft/vscode",
  "pr_count": 1247,
  "avg_interval_seconds": 3600.5,
  "avg_interval_human": {
    "hours": 1.0,
    "days": 0.042
  }
}
```

#### `get_event_counts(offset_minutes: int)`
Get total event counts by type for a time window.

**Example**:
```
offset_minutes: 10
Returns: {
  "offset_minutes": 10,
  "total_events": 45,
  "counts": {
    "WatchEvent": 20,
    "PullRequestEvent": 15,
    "IssuesEvent": 10
  }
}
```

#### `get_repository_activity(repo: str, hours: int = 24)`
Get detailed activity breakdown for a specific repository.

### Resources (Application-Controlled Data)

#### `github://events/status`
Real-time server status including:
- Total events processed
- Unique repositories tracked
- Event type distribution
- Server health metrics

#### `github://events/recent/{event_type}`
Recent events of specified type (WatchEvent, PullRequestEvent, IssuesEvent)

### Prompts (User-Controlled Templates)

#### `analyze_repository_trends(repo: str)`
Generate comprehensive analysis prompt for repository activity patterns.

#### `create_monitoring_alert(threshold_minutes: int = 60)`
Create monitoring and alerting strategy based on current activity levels.

## 📈 Metrics & Analytics

The server provides several key metrics:

### Pull Request Metrics
- **Average time between PRs**: Statistical analysis of PR frequency
- **PR velocity trends**: Patterns in development activity
- **Repository health indicators**: Activity-based health scoring

### Event Metrics  
- **Event count by type**: Distribution across WatchEvent, PullRequestEvent, IssuesEvent
- **Time-based analysis**: Activity patterns over configurable time windows
- **Repository comparison**: Cross-repository activity analysis

### Performance Metrics
- **Polling efficiency**: API rate limit utilization
- **Database performance**: Query execution statistics
- **System health**: Server status and resource utilization

## 🗄️ Database Schema

### Events Table
```sql
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    gh_id TEXT UNIQUE NOT NULL,
    repo_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    payload JSONB
);
```

### Aggregates Table (Performance Optimization)
```sql
CREATE TABLE event_aggregates (
    repo_name TEXT,
    event_type TEXT,
    minute_bucket TIMESTAMPTZ,
    event_count INTEGER,
    PRIMARY KEY (repo_name, event_type, minute_bucket)
);
```

## 🔍 Example Usage Scenarios

### 1. Development Team Monitoring

```
User: "Analyze the recent activity for facebook/react"

MCP Tools Used:
- get_repository_activity("facebook/react", 168)  # 1 week
- get_avg_pr_interval("facebook/react")

AI Response: Provides comprehensive analysis of React repository activity,
PR frequency, community engagement, and development velocity trends.
```

### 2. Project Health Assessment

```
User: "How active has the Kubernetes project been in the last 24 hours?"

MCP Resources Used:
- github://events/status
- github://events/recent/PullRequestEvent

AI Response: Real-time assessment of Kubernetes project health based on
recent GitHub activity patterns.
```

### 3. Competitive Analysis

```
User: "Compare the development velocity between Vue.js and React"

MCP Tools Used:
- get_avg_pr_interval("vuejs/vue")
- get_avg_pr_interval("facebook/react")
- get_repository_activity() for both repos

AI Response: Detailed comparison of development patterns, community
engagement, and project velocity metrics.
```

## 🛡️ Security & Best Practices

### API Rate Limiting
- Implements GitHub's recommended ETag caching
- Respects `X-RateLimit-*` headers
- Exponential backoff on rate limit hits
- Optional GitHub token for 5000 req/hour limit

### Data Privacy
- Only stores public GitHub event data
- No sensitive information logged
- Configurable data retention policies
- GDPR-compliant data handling

### Error Handling
- Comprehensive exception handling
- Circuit breaker patterns for external APIs  
- Graceful degradation on service failures
- Detailed logging for debugging

## 📚 MCP Compliance

This implementation fully complies with MCP specifications:

✅ **JSON-RPC 2.0**: All communication uses standard JSON-RPC messages  
✅ **Capability Negotiation**: Proper initialization and capability exchange  
✅ **Tool Schema**: Automatic schema generation from Python type hints  
✅ **Resource URIs**: RESTful resource naming conventions  
✅ **Prompt Templates**: Dynamic prompt generation with parameters  
✅ **Error Handling**: Standard MCP error responses  
✅ **Transport Support**: STDIO transport for MCP client integration  

## 🧪 Testing

### Unit Tests
```bash
python -m pytest tests/
```

### Integration Tests  
```bash
python -m pytest tests/integration/
```

### Load Testing
```bash
python scripts/load_test.py
```

## 📖 API Documentation

### OpenAPI Documentation
When running in development mode, API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### MCP Schema
The server automatically generates and provides MCP tool schemas following JSON Schema specifications.

## 🐛 Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Verify connection string
psql $DATABASE_URL -c "SELECT 1;"
```

**GitHub API Rate Limiting**
```bash
# Check current rate limit
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     https://api.github.com/rate_limit
```

**MCP Client Connection Issues**
```bash
# Test MCP server directly
python github_events_mcp_server.py

# Check logs
tail -f logs/github_events.log
```

### Debug Mode
Set `LOG_LEVEL=DEBUG` in your environment for detailed logging.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `python -m pytest`
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Run code formatting
black .
isort .

# Run linting
flake8 .
mypy .
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Anthropic** for the Model Context Protocol specification
- **GitHub** for the comprehensive Events API
- **FastMCP** for the excellent Python MCP SDK
- **PostgreSQL** for robust data storage capabilities

---

## 🚀 Next Steps

This implementation provides a solid foundation for GitHub Events monitoring. Consider these enhancements:

1. **Real-time Dashboards**: Build web dashboards using the MCP data
2. **Advanced Analytics**: Implement ML-based anomaly detection  
3. **Webhook Integration**: Add GitHub webhook support for instant updates
4. **Multi-tenant Support**: Scale to support multiple organizations
5. **Custom Metrics**: Add domain-specific KPI calculations
6. **Integration Plugins**: Connect with Slack, Teams, email notifications

---

*Built with ❤️ for the developer community*