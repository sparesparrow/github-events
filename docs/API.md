# API Documentation

## Overview

The GitHub Events Monitor provides a comprehensive REST API for querying GitHub event metrics and an MCP server for AI tool integration.

## Base URL

- **Local Development**: `http://localhost:8000`
- **Docker**: `http://localhost:8000` (default, configurable via `API_PORT`)
- **Production**: Your deployed domain

## Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Spec**: `http://localhost:8000/openapi.json`

## Authentication

The API currently does not require authentication as it only serves aggregated metrics from public GitHub data. The application uses a GitHub token internally for higher rate limits, but clients don't need to provide credentials.

## Supported GitHub Events

The GitHub Events Monitor now supports **23 different GitHub event types** for comprehensive repository monitoring:

### Core Development Events
- **WatchEvent** - Repository stars/watching
- **PullRequestEvent** - Pull requests opened/closed/merged  
- **IssuesEvent** - Issues opened/closed/labeled
- **PushEvent** - Code pushes to repositories
- **ForkEvent** - Repository forks
- **CreateEvent** - Branch/tag creation
- **DeleteEvent** - Branch/tag deletion
- **ReleaseEvent** - Releases published

### Collaboration Events
- **CommitCommentEvent** - Comments on commits
- **IssueCommentEvent** - Comments on issues
- **PullRequestReviewEvent** - PR reviews
- **PullRequestReviewCommentEvent** - Comments on PR reviews

### Repository Management Events
- **PublicEvent** - Repository made public
- **MemberEvent** - Collaborators added/removed
- **TeamAddEvent** - Teams added to repositories

### Security and Maintenance Events
- **GollumEvent** - Wiki pages created/updated
- **DeploymentEvent** - Deployments created
- **DeploymentStatusEvent** - Deployment status updates
- **StatusEvent** - Commit status updates
- **CheckRunEvent** - Check runs completed
- **CheckSuiteEvent** - Check suites completed

### GitHub-Specific Events
- **SponsorshipEvent** - Sponsorship changes
- **MarketplacePurchaseEvent** - Marketplace purchases

## Core Metrics Endpoints (Assignment Requirements)

### Get Event Counts by Type

Returns the total number of events grouped by event type for a given time offset.

```http
GET /metrics/event-counts?offset_minutes={minutes}
```

**Parameters:**
- `offset_minutes` (integer, optional): How many minutes to look back. Default: 60

**Response:**
```json
{
  "offset_minutes": 60,
  "total_events": 150,
  "counts": {
    "WatchEvent": 75,
    "PullRequestEvent": 45,
    "IssuesEvent": 30
  },
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

**Example:**
```bash
# Get events from last 60 minutes
curl "http://localhost:8000/metrics/event-counts?offset_minutes=60"

# Get events from last 24 hours
curl "http://localhost:8000/metrics/event-counts?offset_minutes=1440"
```

### Get Average Pull Request Interval

Calculates the average time between pull requests for a given repository.

```http
GET /metrics/pr-interval?repo={owner}/{repo}
```

**Parameters:**
- `repo` (string, required): Repository in format "owner/repo"

**Response:**
```json
{
  "repo": "owner/repo",
  "total_prs": 25,
  "avg_interval_hours": 8.5,
  "avg_interval_seconds": 30600,
  "median_interval_hours": 6.2,
  "min_interval_hours": 0.5,
  "max_interval_hours": 72.0,
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

**Example:**
```bash
# Get PR intervals for a specific repository
curl "http://localhost:8000/metrics/pr-interval?repo=microsoft/vscode"
```

## Enhanced Monitoring Endpoints

### Get Repository Health Score

Returns comprehensive repository health assessment based on multiple metrics.

```http
GET /metrics/repository-health?repo={owner}/{repo}&hours={hours}
```

**Parameters:**
- `repo` (string, required): Repository in format "owner/repo"
- `hours` (integer, optional): Time window in hours. Default: 168 (1 week)

**Response:**
```json
{
  "repo_name": "microsoft/vscode",
  "analysis_period_hours": 168,
  "total_events": 245,
  "health_score": 87.5,
  "activity_score": 92.0,
  "collaboration_score": 85.0,
  "maintenance_score": 88.0,
  "security_score": 85.0,
  "activity_breakdown": {
    "PushEvent": 45,
    "PullRequestEvent": 32,
    "IssuesEvent": 18
  },
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

### Get Developer Productivity Metrics

Analyzes individual developer contributions and productivity.

```http
GET /metrics/developer-productivity?repo={owner}/{repo}&hours={hours}
```

**Response:**
```json
{
  "repo": "microsoft/vscode",
  "hours": 168,
  "developers": [
    {
      "actor_login": "developer1",
      "total_events": 45,
      "pushes": 12,
      "prs_opened": 3,
      "reviews_given": 8,
      "productivity_score": 89.5,
      "event_diversity": 83.3
    }
  ]
}
```

### Get Security Monitoring Report

Monitors security-related activities and provides risk assessment.

```http
GET /metrics/security-monitoring?repo={owner}/{repo}&hours={hours}
```

**Response:**
```json
{
  "repo_name": "microsoft/vscode",
  "security_score": 85.0,
  "risk_level": "low",
  "security_events": {
    "CheckRunEvent": 45,
    "StatusEvent": 67
  },
  "recommendations": [],
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

### Detect Event Anomalies

Detects unusual patterns in repository activity.

```http
GET /metrics/event-anomalies?repo={owner}/{repo}&hours={hours}
```

**Response:**
```json
{
  "repo": "microsoft/vscode",
  "hours": 168,
  "anomalies": [
    {
      "type": "spike",
      "event_type": "WatchEvent",
      "severity": "high",
      "description": "Unusual spike in WatchEvent activity",
      "threshold": 15.2,
      "actual_value": 45.0,
      "confidence": 0.95
    }
  ]
}
```

### Get Release and Deployment Metrics

Tracks release and deployment patterns.

```http
GET /metrics/release-deployment?repo={owner}/{repo}&hours={hours}
```

**Parameters:**
- `hours` (integer, optional): Default: 720 (30 days)

**Response:**
```json
{
  "repo_name": "microsoft/vscode",
  "releases": {
    "total_count": 8,
    "frequency_per_week": 1.2
  },
  "deployments": {
    "total_count": 24,
    "success_rate": 91.7
  },
  "deployment_lead_time": 4.5
}
```

### Get Community Engagement Metrics

Analyzes community health and engagement.

```http
GET /metrics/community-engagement?repo={owner}/{repo}&hours={hours}
```

**Response:**
```json
{
  "repo_name": "microsoft/vscode",
  "total_contributors": 45,
  "active_contributors": 23,
  "community_health_score": 78.5,
  "top_contributors": [
    {
      "actor_login": "contributor1",
      "engagement_score": 45.0
    }
  ]
}
```

### Get Event Types Summary

Provides comprehensive overview of all monitored event types.

```http
GET /metrics/event-types-summary?repo={owner}/{repo}&hours={hours}
```

**Response:**
```json
{
  "repo": "microsoft/vscode",
  "total_monitored_events": 23,
  "total_events": 245,
  "event_types": {
    "PushEvent": {
      "count": 45,
      "description": "Code pushes to repositories",
      "category": "development"
    }
  },
  "categories": {
    "development": {
      "count": 120,
      "event_types": ["PushEvent", "PullRequestEvent"]
    }
  }
}
```

## Additional Metrics Endpoints

### Get Repository Activity

Returns detailed activity summary for a specific repository.

```http
GET /metrics/repository-activity?repo={owner}/{repo}&hours={hours}
```

**Parameters:**
- `repo` (string, required): Repository in format "owner/repo"
- `hours` (integer, optional): Time window in hours. Default: 24

**Response:**
```json
{
  "repo": "owner/repo",
  "hours": 24,
  "total_events": 45,
  "event_breakdown": {
    "WatchEvent": 20,
    "PullRequestEvent": 15,
    "IssuesEvent": 10
  },
  "unique_actors": 12,
  "activity_score": 85.5,
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

### Get Trending Repositories

Returns repositories with the most activity in a specified time window.

```http
GET /metrics/trending?hours={hours}&limit={limit}

### New Monitoring Use Cases

The API now exposes additional metrics derived from more GitHub event types (PushEvent, ReleaseEvent, IssueCommentEvent, PullRequestReviewEvent, PullRequestReviewCommentEvent, ForkEvent, CreateEvent, DeleteEvent):

- `GET /metrics/stars?hours={hours}&repo={owner}/{repo}`
  - Returns star count (WatchEvent) in the last N hours; `repo` optional for global.
  - Example:
    ```bash
    curl "http://localhost:8000/metrics/stars?hours=24&repo=microsoft/vscode"
    ```

- `GET /metrics/releases?hours={hours}&repo={owner}/{repo}`
  - Returns number of published releases (ReleaseEvent with action=published) in last N hours.
  - Example:
    ```bash
    curl "http://localhost:8000/metrics/releases?hours=168&repo=hashicorp/terraform"
    ```

- `GET /metrics/push-activity?hours={hours}&repo={owner}/{repo}`
  - Returns push activity stats: `{ push_events, total_commits }` over last N hours.
  - Example:
    ```bash
    curl "http://localhost:8000/metrics/push-activity?hours=24&repo=vercel/next.js"
    ```

- `GET /metrics/pr-merge-time?repo={owner}/{repo}&hours={hours}`
  - Average PR merge time for PRs opened in last N hours and later merged.
  - Response includes: `avg_seconds`, `p50`, `p90`, and `count`.
  - Example:
    ```bash
    curl "http://localhost:8000/metrics/pr-merge-time?repo=facebook/react&hours=336"
    ```

- `GET /metrics/issue-first-response?repo={owner}/{repo}&hours={hours}`
  - Average time to first comment on issues opened in last N hours.
  - Response includes: `avg_seconds`, `p50`, `p90`, and `count`.
  - Example:
    ```bash
    curl "http://localhost:8000/metrics/issue-first-response?repo=pallets/flask&hours=336"
    ```
```

**Parameters:**
- `hours` (integer, optional): Time window in hours. Default: 24
- `limit` (integer, optional): Maximum number of repositories to return. Default: 10

**Response:**
```json
{
  "hours": 24,
  "limit": 10,
  "repositories": [
    {
      "repo": "microsoft/vscode",
      "total_events": 245,
      "watch_events": 120,
      "pr_events": 85,
      "issues_events": 40,
      "activity_score": 95.5
    },
    {
      "repo": "facebook/react",
      "total_events": 180,
      "watch_events": 90,
      "pr_events": 60,
      "issues_events": 30,
      "activity_score": 87.2
    }
  ],
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

## Visualization Endpoints (Bonus)

### Get Trending Chart

Generates a chart visualization of trending repositories.

```http
GET /visualization/trending-chart?hours={hours}&limit={limit}&format={format}
```

**Parameters:**
- `hours` (integer, optional): Time window in hours. Default: 24
- `limit` (integer, optional): Number of repositories to include. Default: 5
- `format` (string, optional): Output format ("png", "svg"). Default: "png"

**Response:**
- Content-Type: `image/png` or `image/svg+xml`
- Binary image data

**Example:**
```bash
# Get PNG chart of top 5 trending repositories
curl "http://localhost:8000/visualization/trending-chart?hours=24&limit=5&format=png" \
  --output trending_chart.png

# Get SVG chart
curl "http://localhost:8000/visualization/trending-chart?format=svg" \
  --output trending_chart.svg
```

### Get Pull Request Timeline

Generates a timeline chart of pull request activity for a repository.

```http
GET /visualization/pr-timeline?repo={owner}/{repo}&hours={hours}&format={format}
```

**Parameters:**
- `repo` (string, required): Repository in format "owner/repo"
- `hours` (integer, optional): Time window in hours. Default: 168 (1 week)
- `format` (string, optional): Output format ("png", "svg"). Default: "png"

**Response:**
- Content-Type: `image/png` or `image/svg+xml`
- Binary image data

## System Endpoints

### Health Check

Returns the current system health and status.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "database_path": "/app/data/github_events.db",
  "github_token_configured": true,
  "last_poll_timestamp": "2025-08-21T19:45:00.000000+00:00",
  "total_events_stored": 15420,
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

### Manual Event Collection

Triggers manual collection of events from GitHub API.

```http
POST /collect
```

**Response:**
```json
{
  "status": "success",
  "events_collected": 25,
  "new_events": 18,
  "duplicate_events": 7,
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

## Error Handling

The API uses standard HTTP status codes and returns consistent error responses.

### Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

### Common Error Codes

- `400 Bad Request`: Invalid parameters or request format
- `404 Not Found`: Requested resource not found
- `422 Unprocessable Entity`: Invalid input data
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: External service (GitHub) unavailable

### Example Error Responses

```json
// Invalid repository format
{
  "detail": "Repository must be in format 'owner/repo'",
  "error_code": "INVALID_REPO_FORMAT",
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}

// Insufficient data
{
  "detail": "Insufficient pull request data for repository 'owner/repo'",
  "error_code": "INSUFFICIENT_DATA",
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

## Rate Limiting

The API implements basic rate limiting to prevent abuse:

- **Default**: 100 requests per minute per IP
- **Burst**: Up to 10 requests per second
- **Headers**: Rate limit information in response headers

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1692639997
```

## MCP Server Integration

The application also provides a Model Context Protocol (MCP) server for AI tool integration.

### MCP Tools

#### get_event_counts

Retrieve event counts with time filtering.

**Parameters:**
- `offset_minutes` (integer, optional): Time offset in minutes

**Example Usage in Claude Desktop:**
```
Get event counts for the last 2 hours
```

#### get_repository_activity

Get detailed activity for a specific repository.

**Parameters:**
- `repo` (string, required): Repository name
- `hours` (integer, optional): Time window

**Example Usage:**
```
Show me activity for microsoft/vscode in the last 24 hours
```

#### get_trending_repositories

Find trending repositories based on activity.

**Parameters:**
- `hours` (integer, optional): Time window
- `limit` (integer, optional): Maximum results

**Example Usage:**
```
What are the top 10 trending repositories today?
```

#### get_avg_pr_interval

Calculate average time between pull requests.

**Parameters:**
- `repo` (string, required): Repository name

**Example Usage:**
```
What's the average time between PRs for facebook/react?
```

#### get_repository_health_score

Get comprehensive repository health assessment.

**Parameters:**
- `repo` (string, required): Repository name
- `hours` (integer, optional): Time window

**Example Usage:**
```
Assess the health of microsoft/vscode repository
```

#### get_developer_productivity_metrics

Analyze developer productivity and contributions.

**Parameters:**
- `repo` (string, required): Repository name
- `hours` (integer, optional): Time window

**Example Usage:**
```
Show me the most productive developers in kubernetes/kubernetes
```

#### get_security_monitoring_report

Generate security monitoring report.

**Parameters:**
- `repo` (string, required): Repository name
- `hours` (integer, optional): Time window

**Example Usage:**
```
Check security posture of tensorflow/tensorflow
```

#### detect_event_anomalies

Detect unusual patterns in repository activity.

**Parameters:**
- `repo` (string, required): Repository name
- `hours` (integer, optional): Time window

**Example Usage:**
```
Find any unusual activity in golang/go repository
```

#### get_release_deployment_metrics

Analyze release and deployment patterns.

**Parameters:**
- `repo` (string, required): Repository name
- `hours` (integer, optional): Time window (default: 720)

**Example Usage:**
```
Show deployment metrics for nodejs/node
```

#### get_community_engagement_metrics

Analyze community health and engagement.

**Parameters:**
- `repo` (string, required): Repository name
- `hours` (integer, optional): Time window

**Example Usage:**
```
How healthy is the Python community engagement?
```

### MCP Resources

- `recent-events`: Access to recent event data
- `repository-metrics`: Repository-specific metrics
- `trending-data`: Trending repository information

### MCP Prompts

- `analyze_repository_trends`: Analyze repository activity patterns
- `create_monitoring_dashboard_config`: Generate monitoring configurations
- `compare_repository_activity`: Compare activity between repositories

## Client Examples

### Python Client

```python
import requests

class GitHubEventsClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def get_event_counts(self, offset_minutes=60):
        response = requests.get(
            f"{self.base_url}/metrics/event-counts",
            params={"offset_minutes": offset_minutes}
        )
        return response.json()
    
    def get_pr_interval(self, repo):
        response = requests.get(
            f"{self.base_url}/metrics/pr-interval",
            params={"repo": repo}
        )
        return response.json()
    
    def get_health(self):
        response = requests.get(f"{self.base_url}/health")
        return response.json()

# Usage
client = GitHubEventsClient()
health = client.get_health()
events = client.get_event_counts(120)  # Last 2 hours
pr_data = client.get_pr_interval("microsoft/vscode")
```

### JavaScript Client

```javascript
class GitHubEventsClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async getEventCounts(offsetMinutes = 60) {
        const response = await fetch(
            `${this.baseUrl}/metrics/event-counts?offset_minutes=${offsetMinutes}`
        );
        return response.json();
    }
    
    async getPrInterval(repo) {
        const response = await fetch(
            `${this.baseUrl}/metrics/pr-interval?repo=${encodeURIComponent(repo)}`
        );
        return response.json();
    }
    
    async getHealth() {
        const response = await fetch(`${this.baseUrl}/health`);
        return response.json();
    }
}

// Usage
const client = new GitHubEventsClient();
const health = await client.getHealth();
const events = await client.getEventCounts(120);
const prData = await client.getPrInterval('microsoft/vscode');
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Event counts for last hour
curl "http://localhost:8000/metrics/event-counts?offset_minutes=60"

# PR intervals for a repository
curl "http://localhost:8000/metrics/pr-interval?repo=microsoft/vscode"

# Repository activity for last 24 hours
curl "http://localhost:8000/metrics/repository-activity?repo=facebook/react&hours=24"

# Top 5 trending repositories
curl "http://localhost:8000/metrics/trending?hours=24&limit=5"

# Download trending chart
curl "http://localhost:8000/visualization/trending-chart?format=png" \
  --output trending.png

# Manual event collection
curl -X POST http://localhost:8000/collect

# Enhanced monitoring endpoints

# Repository health assessment
curl "http://localhost:8000/metrics/repository-health?repo=microsoft/vscode&hours=168"

# Developer productivity analysis
curl "http://localhost:8000/metrics/developer-productivity?repo=facebook/react&hours=720"

# Security monitoring report
curl "http://localhost:8000/metrics/security-monitoring?repo=kubernetes/kubernetes&hours=168"

# Event anomaly detection
curl "http://localhost:8000/metrics/event-anomalies?repo=tensorflow/tensorflow&hours=168"

# Release and deployment metrics
curl "http://localhost:8000/metrics/release-deployment?repo=nodejs/node&hours=2160"

# Community engagement analysis
curl "http://localhost:8000/metrics/community-engagement?repo=python/cpython&hours=168"

# Complete event types overview
curl "http://localhost:8000/metrics/event-types-summary?repo=golang/go&hours=168"
```

## WebSocket Support (Future Enhancement)

Future versions may include WebSocket support for real-time updates:

```javascript
// Future WebSocket API (not yet implemented)
const ws = new WebSocket('ws://localhost:8000/ws/events');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('New events:', data);
};
```

## GraphQL Support (Future Enhancement)

Future versions may include GraphQL API for flexible queries:

```graphql
# Future GraphQL API (not yet implemented)
query {
  repository(name: "microsoft/vscode") {
    activity(hours: 24) {
      totalEvents
      eventBreakdown {
        watchEvents
        pullRequestEvents
        issuesEvents
      }
    }
    pullRequestMetrics {
      averageInterval
      medianInterval
    }
  }
}
```

## Performance Considerations

- **Response Times**: Most endpoints respond within 100ms
- **Caching**: Results are computed in real-time from stored data
- **Concurrency**: FastAPI handles multiple concurrent requests efficiently
- **Rate Limiting**: Prevents abuse while allowing normal usage patterns

## Security Notes

- **Public Data Only**: API only serves aggregated public GitHub data
- **No Authentication**: Currently no authentication required
- **Input Validation**: All inputs validated with Pydantic models
- **SQL Injection**: Protected by parameterized queries
- **CORS**: Configurable for web client integration