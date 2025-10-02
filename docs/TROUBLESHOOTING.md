# Troubleshooting Guide

## Common Issues and Solutions

### API and Database Issues

#### Issue: "RuntimeError: threads can only be started once"
**Symptoms**: API crashes when accessing database endpoints

**Cause**: Database connection was being used incorrectly with async context managers

**Solution**: ✅ Fixed in latest version. The `DBConnection.connect()` now properly uses `@asynccontextmanager`.

```python
# ✅ Correct usage (now)
async with self.db.connect() as conn:
    await conn.execute(query)

# ❌ Wrong usage (old)
async with await self.db.connect() as conn:
    await conn.execute(query)
```

#### Issue: "Query service not wired"
**Symptoms**: API returns 500 error with "Query service not wired" message

**Cause**: FastAPI dependency injection not properly configured

**Solution**: ✅ Fixed. Services are now wired using module-level singletons set before router registration.

#### Issue: Empty results from metrics endpoints
**Symptoms**: Endpoints return `{}` or empty arrays

**Cause**: No data has been collected yet

**Solution**:
```bash
# Collect some events first
curl -X POST "http://localhost:8000/collect?limit=100"

# Then query metrics
curl "http://localhost:8000/metrics/event-counts?offset_minutes=60"
```

### Import and Module Issues

#### Issue: "ModuleNotFoundError: No module named 'github_events_monitor'"
**Symptoms**: Tests or scripts fail with import errors

**Cause**: Incorrect import paths or missing `src` in path

**Solution**:
```python
# ✅ Correct imports
from src.github_events_monitor.api import app
from src.github_events_monitor.event_collector import GitHubEventsCollector

# ❌ Wrong imports (old structure)
from github_events_monitor.api import app
```

Or set PYTHONPATH:
```bash
export PYTHONPATH=/workspace/src:$PYTHONPATH
```

### CI/CD Issues

#### Issue: GitHub Pages deployment fails
**Symptoms**: Workflow completes but pages are empty or broken

**Cause**: JSON files not generated correctly

**Solution**: Check that the API server started and the export step completed:
```yaml
- name: Verify pages_content directory
  run: |
    ls -la pages_content/
    for f in pages_content/*.json; do
      echo "=== $f ==="
      head -n 3 "$f"
    done
```

#### Issue: Database artifact not restored
**Symptoms**: Dashboard shows no historical data

**Cause**: Database artifact expired or not found

**Solution**: The workflow automatically handles this with fallback to empty database. For manual restoration:
```bash
# Download artifact manually
gh run download <run-id> -n github_events_db

# Or trigger manual update
gh workflow run manual-update-db.yml
```

### Testing Issues

#### Issue: Tests fail with import errors
**Symptoms**: `pytest` collection fails

**Solution**: Update test imports to use `src.github_events_monitor` paths:
```python
# In tests
from src.github_events_monitor.event_collector import GitHubEventsCollector
from src.github_events_monitor.event import GitHubEvent
```

#### Issue: MCP configuration tests fail with "File not found"
**Symptoms**: MCP tests report missing configuration files

**Cause**: MCP configuration files don't exist (tests are outdated)

**Solution**: Either create the configuration files or skip these tests:
```bash
pytest -k "not mcp_configuration"
```

### Docker Issues

#### Issue: Container fails to start
**Symptoms**: Docker container exits immediately

**Solution**: Check logs and ensure database path is mounted:
```bash
docker logs <container-id>

# Ensure volume is mounted
docker run -v $(pwd)/data:/app/data \
  -e DATABASE_PATH=/app/data/github_events.db \
  github-events-monitor
```

#### Issue: API not accessible from host
**Symptoms**: `curl localhost:8000` connection refused

**Solution**: Ensure ports are published and host is set to 0.0.0.0:
```bash
docker run -p 8000:8000 \
  -e API_HOST=0.0.0.0 \
  -e API_PORT=8000 \
  github-events-monitor
```

### Performance Issues

#### Issue: Slow query responses
**Symptoms**: API endpoints take several seconds to respond

**Cause**: Missing database indexes or large dataset

**Solution**:
1. Check if indexes exist:
```sql
PRAGMA index_list('events');
```

2. Add missing indexes:
```sql
CREATE INDEX IF NOT EXISTS idx_events_type_ts ON events(event_type, created_at_ts);
CREATE INDEX IF NOT EXISTS idx_events_repo_ts ON events(repo_name, created_at_ts);
```

3. Analyze query plans:
```sql
EXPLAIN QUERY PLAN 
SELECT event_type, COUNT(*) 
FROM events 
WHERE created_at_ts >= ? 
GROUP BY event_type;
```

#### Issue: High memory usage
**Symptoms**: Application consumes excessive memory

**Cause**: Too many events loaded into memory at once

**Solution**: Use pagination and limit query results:
```python
# Limit historical queries
since_ts = int((datetime.now() - timedelta(days=7)).timestamp())

# Use LIMIT in queries
cursor.execute("SELECT * FROM events ORDER BY created_at_ts DESC LIMIT 1000")
```

### GitHub API Issues

#### Issue: Rate limit exceeded
**Symptoms**: Collection fails with 403 or 429 errors

**Cause**: Too many requests without authentication

**Solution**: Set GITHUB_TOKEN environment variable:
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

Check rate limit status:
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

#### Issue: No events collected for specific repositories
**Symptoms**: TARGET_REPOSITORIES set but no data

**Cause**: Repository doesn't have public events or events are older than GitHub's retention

**Solution**: Check repository activity:
```bash
# Verify repository has recent events
curl "https://api.github.com/repos/owner/repo/events"
```

Note: GitHub only provides events from the last 90 days.

## Debugging Tips

### Enable Detailed Logging
```python
# In your environment or config
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Check Database Contents
```bash
# SQLite command-line
sqlite3 github_events.db

# List tables
.tables

# Check event counts
SELECT event_type, COUNT(*) FROM events GROUP BY event_type;

# Check recent events
SELECT created_at, repo_name, event_type FROM events 
ORDER BY created_at_ts DESC LIMIT 10;
```

### Monitor API Performance
```bash
# Use httpie for better formatted output
http GET localhost:8000/health

# Check response times
time curl -s "http://localhost:8000/metrics/trending?hours=24"
```

### Test Individual Components
```python
# Test database connection
import asyncio
from src.github_events_monitor.infrastructure.db_connection import DBConnection

async def test_db():
    db = DBConnection("./test.db")
    await db.initialize()
    async with db.connect() as conn:
        await conn.execute("SELECT 1")
        print("✅ Database connection working")

asyncio.run(test_db())
```

### Validate JSON Output
```bash
# Verify JSON is valid
curl -s "http://localhost:8000/metrics/event-counts" | python3 -m json.tool

# Check for specific fields
curl -s "http://localhost:8000/metrics/trending" | jq '.items[0]'
```

## Getting Help

### Information to Include in Bug Reports
1. Operating system and Python version
2. Error messages and stack traces
3. Relevant configuration (DATABASE_PATH, TARGET_REPOSITORIES, etc.)
4. Steps to reproduce the issue
5. Log output with DEBUG level enabled

### Useful Commands for Diagnostics
```bash
# System information
python3 --version
pip list | grep -E "(fastapi|aiosqlite|httpx)"

# Check if API is running
netstat -tulpn | grep 8000
ps aux | grep "github_events_monitor"

# Database diagnostics
sqlite3 github_events.db "PRAGMA integrity_check;"
sqlite3 github_events.db "SELECT COUNT(*) FROM events;"

# API diagnostics
curl -v http://localhost:8000/health
curl -v http://localhost:8000/docs
```

## Preventive Measures

### Regular Maintenance
1. **Database Cleanup**: Archive old events after 90 days
2. **Index Optimization**: Run ANALYZE periodically
3. **Log Rotation**: Prevent log files from growing too large
4. **Dependency Updates**: Keep dependencies up to date for security

### Monitoring
1. Set up health check alerts
2. Monitor API response times
3. Track GitHub API rate limit usage
4. Monitor database size and growth

### Best Practices
1. Always use GITHUB_TOKEN for higher rate limits
2. Set appropriate POLL_INTERVAL (default 300 seconds)
3. Use DATABASE_PROVIDER=dynamodb for production scale
4. Enable CORS_ORIGINS=* only in development
5. Run database migrations before deploying updates

## Quick Reference

### Environment Variables
```bash
# Required
GITHUB_TOKEN=ghp_xxxxx              # GitHub personal access token

# Optional
DATABASE_PATH=./github_events.db     # SQLite database path
DATABASE_PROVIDER=sqlite             # or 'dynamodb'
TARGET_REPOSITORIES=owner/repo       # Comma-separated list
POLL_INTERVAL=300                    # Seconds between polls
API_HOST=0.0.0.0                     # API bind address
API_PORT=8000                        # API port
CORS_ORIGINS=*                       # CORS allowed origins
```

### Useful Endpoints
```
GET  /health                         # Health check
GET  /docs                           # OpenAPI documentation
POST /collect?limit=100              # Collect events
GET  /metrics/event-counts           # Event type counts
GET  /metrics/trending               # Trending repositories
GET  /metrics/repository-activity    # Repository activity
```

### Common pytest Commands
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_api.py

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x

# Run tests matching pattern
pytest -k "not mcp"

# Show print output
pytest -s
```
