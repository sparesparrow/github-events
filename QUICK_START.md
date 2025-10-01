# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.11+
- pip or uv package manager
- (Optional) GitHub Personal Access Token for higher rate limits

### Installation

#### Option 1: pip (Recommended)
```bash
# Clone the repository
git clone https://github.com/sparesparrow/github-events-clone.git
cd github-events-clone

# Install dependencies
pip install -r requirements.txt

# (Optional) Install in development mode
pip install -e .
```

#### Option 2: Docker
```bash
# Quick start with Docker Compose
docker-compose up -d

# Access API at http://localhost:8000
```

### Start the API Server

```bash
# Basic start (uses SQLite by default)
python3 -m src.github_events_monitor.api

# With GitHub token (recommended for higher rate limits)
export GITHUB_TOKEN=ghp_your_token_here
python3 -m src.github_events_monitor.api

# Monitor specific repositories
export TARGET_REPOSITORIES=owner/repo1,owner/repo2
python3 -m src.github_events_monitor.api
```

The API will be available at `http://localhost:8000`

### Collect Some Data

```bash
# Collect 100 events from GitHub
curl -X POST "http://localhost:8000/collect?limit=100"

# Response: {"inserted": 100}
```

### View the Data

```bash
# Check health
curl "http://localhost:8000/health"

# Get event counts (last 60 minutes)
curl "http://localhost:8000/metrics/event-counts?offset_minutes=60"

# Get trending repositories (last 24 hours)
curl "http://localhost:8000/metrics/trending?hours=24&limit=10"

# View interactive documentation
open http://localhost:8000/docs
```

## 🎯 Common Use Cases

### Monitor Specific Repositories
```bash
export TARGET_REPOSITORIES=kubernetes/kubernetes,docker/compose
python3 -m src.github_events_monitor.api
```

### Run Continuously with Polling
The application automatically polls GitHub every 5 minutes (configurable):
```bash
export POLL_INTERVAL=300  # seconds
python3 -m src.github_events_monitor.api
```

### Use DynamoDB for Production
```bash
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-west-2
export DYNAMODB_TABLE_PREFIX=github-events-

# Create tables (first time only)
python3 scripts/setup_dynamodb.py create

# Start API
python3 -m src.github_events_monitor.api
```

## 📊 API Endpoints Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | Interactive API documentation |
| `/collect` | POST | Manually collect events |
| `/metrics/event-counts` | GET | Event counts by type |
| `/metrics/trending` | GET | Trending repositories |
| `/metrics/repository-activity` | GET | Repository activity summary |
| `/metrics/stars` | GET | Star events |
| `/metrics/releases` | GET | Release events |
| `/metrics/push-activity` | GET | Push events and commits |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_api.py

# Run with verbose output
pytest -v

# Run tests and show coverage
pytest --cov=src/github_events_monitor
```

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | None |
| `DATABASE_PATH` | SQLite database path | `./github_events.db` |
| `DATABASE_PROVIDER` | `sqlite` or `dynamodb` | `sqlite` |
| `TARGET_REPOSITORIES` | Comma-separated repo list | None (all events) |
| `POLL_INTERVAL` | Polling interval (seconds) | 300 |
| `API_HOST` | API bind address | `0.0.0.0` |
| `API_PORT` | API port | 8000 |
| `CORS_ORIGINS` | CORS allowed origins | None |

## 🔍 Troubleshooting

### Problem: "Module not found" errors
```bash
# Solution: Add src to PYTHONPATH
export PYTHONPATH=/workspace/src:$PYTHONPATH
```

### Problem: "Connection refused" to API
```bash
# Check if API is running
ps aux | grep github_events_monitor

# Check if port is in use
netstat -tulpn | grep 8000

# Try different port
export API_PORT=8080
python3 -m src.github_events_monitor.api
```

### Problem: Empty results from metrics
```bash
# Collect some data first
curl -X POST "http://localhost:8000/collect?limit=100"

# Then query
curl "http://localhost:8000/metrics/event-counts"
```

### Problem: GitHub rate limit exceeded
```bash
# Set GitHub token for higher limits
export GITHUB_TOKEN=ghp_your_token_here

# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

## 📚 Learn More

- **Full Documentation**: See `/workspace/docs/README.md`
- **API Reference**: `/workspace/docs/API.md`
- **Troubleshooting**: `/workspace/docs/TROUBLESHOOTING.md`
- **Improvements**: `/workspace/IMPROVEMENTS_AND_REFACTORINGS.md`

## 🎉 That's It!

You now have a fully functional GitHub Events Monitor running. The system will:
- ✅ Automatically collect GitHub events every 5 minutes
- ✅ Store them in a SQLite database
- ✅ Provide real-time metrics and analytics via REST API
- ✅ Offer interactive documentation at `/docs`

For production deployment, see `/workspace/docs/DEPLOYMENT.md`

## Quick Commands Cheatsheet

```bash
# Start API
python3 -m src.github_events_monitor.api

# Collect events
curl -X POST "http://localhost:8000/collect?limit=100"

# Get metrics
curl "http://localhost:8000/metrics/event-counts"

# View docs
open http://localhost:8000/docs

# Run tests
pytest

# Docker start
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop Docker
docker-compose down
```

Happy monitoring! 🚀
