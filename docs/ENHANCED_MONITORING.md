# Enhanced Monitoring Use Cases and GitHub Events

## Overview

The GitHub Events Monitor has been significantly enhanced to support comprehensive repository monitoring across multiple dimensions. This document outlines the new monitoring use cases, supported GitHub events, and API endpoints.

## Supported GitHub Events (Expanded)

The monitor now supports **23 different GitHub event types**, categorized by their purpose:

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

## Enhanced Monitoring Use Cases

### 1. Repository Health Monitoring

**Endpoint:** `GET /metrics/repository-health?repo=owner/repo&hours=168`

Provides comprehensive health assessment including:
- **Overall Health Score** (0-100) - Weighted combination of all metrics
- **Activity Score** - Based on development activity (pushes, PRs, issues)
- **Collaboration Score** - Based on reviews, comments, discussions
- **Maintenance Score** - Based on releases, deployments, CI/CD activity
- **Security Score** - Based on security checks, status updates

**Use Cases:**
- Monitor repository vitality and engagement
- Identify repositories that need attention
- Track health trends over time
- Compare health across multiple repositories

**Example Response:**
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
    "IssuesEvent": 18,
    "PullRequestReviewEvent": 28
  }
}
```

### 2. Developer Productivity Analytics

**Endpoint:** `GET /metrics/developer-productivity?repo=owner/repo&hours=168`

Analyzes individual developer contributions and productivity:
- **Productivity Score** - Weighted score based on various activities
- **Event Diversity** - How many different types of activities
- **Activity Breakdown** - Pushes, PRs, reviews, comments, releases
- **Engagement Timeline** - First and last activity timestamps

**Use Cases:**
- Identify top contributors
- Recognize diverse contributors (not just code)
- Track developer engagement patterns
- Support performance reviews and recognition

**Example Response:**
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
      "comments_made": 15,
      "productivity_score": 89.5,
      "event_diversity": 83.3
    }
  ]
}
```

### 3. Security Monitoring

**Endpoint:** `GET /metrics/security-monitoring?repo=owner/repo&hours=168`

Monitors security-related activities and provides risk assessment:
- **Security Score** (0-100) - Based on security checks and CI/CD
- **Risk Level** - Low/Medium/High assessment
- **Security Events** - Check runs, status updates, deployments
- **Deployment Security** - Environment tracking and success rates
- **Recommendations** - Actionable security improvements

**Use Cases:**
- Monitor security posture of repositories
- Track CI/CD pipeline health
- Identify security gaps and risks
- Ensure compliance with security policies

**Example Response:**
```json
{
  "repo_name": "microsoft/vscode",
  "security_score": 85.0,
  "risk_level": "low",
  "security_events": {
    "CheckRunEvent": 45,
    "CheckSuiteEvent": 23,
    "StatusEvent": 67
  },
  "deployment_security": {
    "total_deployments": 12,
    "environments": {"production": 5, "staging": 7}
  },
  "recommendations": []
}
```

### 4. Event Anomaly Detection

**Endpoint:** `GET /metrics/event-anomalies?repo=owner/repo&hours=168`

Detects unusual patterns in repository activity:
- **Spike Detection** - Unusual increases in activity
- **Drop Detection** - Unusual decreases in activity
- **Confidence Scores** - Statistical confidence in anomalies
- **Severity Levels** - High/Medium/Low severity classification

**Use Cases:**
- Early warning for unusual activity
- Detect potential security incidents
- Identify viral content or sudden popularity
- Monitor for bot activity or spam

**Example Response:**
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

### 5. Release and Deployment Analytics

**Endpoint:** `GET /metrics/release-deployment?repo=owner/repo&hours=720`

Tracks release and deployment patterns:
- **Release Frequency** - Releases per week
- **Deployment Frequency** - Deployments per week
- **Success Rates** - Deployment success percentage
- **Lead Time** - Time from release to deployment
- **Environment Tracking** - Production, staging, development

**Use Cases:**
- Monitor DevOps maturity and practices
- Track deployment pipeline health
- Measure release velocity
- Identify deployment bottlenecks

**Example Response:**
```json
{
  "repo_name": "microsoft/vscode",
  "releases": {
    "total_count": 8,
    "frequency_per_week": 1.2,
    "release_types": {"stable": 6, "prerelease": 2}
  },
  "deployments": {
    "total_count": 24,
    "frequency_per_week": 3.6,
    "success_rate": 91.7,
    "environments": {"production": 8, "staging": 16}
  },
  "deployment_lead_time": 4.5
}
```

### 6. Community Engagement Analytics

**Endpoint:** `GET /metrics/community-engagement?repo=owner/repo&hours=168`

Analyzes community health and engagement:
- **Community Health Score** (0-100) - Overall community vitality
- **Contributor Metrics** - Total, new, and active contributors
- **Engagement Distribution** - High/medium/low engagement levels
- **Top Contributors** - Most engaged community members

**Use Cases:**
- Assess community health and growth
- Identify community champions
- Track contributor retention
- Measure project sustainability

**Example Response:**
```json
{
  "repo_name": "microsoft/vscode",
  "total_contributors": 45,
  "new_contributors": 8,
  "active_contributors": 23,
  "community_health_score": 78.5,
  "engagement_distribution": {
    "high_engagement": 12,
    "medium_engagement": 18,
    "low_engagement": 15
  },
  "top_contributors": [
    {
      "actor_login": "contributor1",
      "engagement_score": 45.0,
      "event_diversity": 6
    }
  ]
}
```

### 7. Event Types Summary

**Endpoint:** `GET /metrics/event-types-summary?repo=owner/repo&hours=168`

Provides comprehensive overview of all monitored event types:
- **Event Categories** - Development, collaboration, deployment, etc.
- **Event Descriptions** - Human-readable descriptions
- **Activity Levels** - Count of each event type
- **Category Summaries** - Grouped statistics

**Use Cases:**
- Understand repository activity patterns
- Identify most active event types
- Compare activity across categories
- Generate comprehensive reports

## Database Schema Enhancements

New tables have been added to support advanced monitoring:

### Repository Health Metrics
```sql
CREATE TABLE repository_health_metrics (
    repo_name TEXT PRIMARY KEY,
    health_score REAL,
    activity_score REAL,
    collaboration_score REAL,
    security_score REAL,
    -- ... additional metrics
);
```

### Developer Metrics
```sql
CREATE TABLE developer_metrics (
    actor_login TEXT,
    repo_name TEXT,
    productivity_score REAL,
    collaboration_score REAL,
    time_period TEXT,
    -- ... activity counts
);
```

### Security Metrics
```sql
CREATE TABLE security_metrics (
    repo_name TEXT,
    metric_type TEXT,
    severity TEXT,
    count INTEGER,
    -- ... security tracking
);
```

### Event Patterns
```sql
CREATE TABLE event_patterns (
    repo_name TEXT,
    event_type TEXT,
    pattern_type TEXT, -- 'spike', 'drop', 'trend', 'anomaly'
    severity TEXT,
    confidence_score REAL,
    -- ... anomaly details
);
```

### Deployment Metrics
```sql
CREATE TABLE deployment_metrics (
    repo_name TEXT,
    deployment_id TEXT,
    environment TEXT,
    status TEXT,
    duration_seconds INTEGER,
    -- ... deployment tracking
);
```

## Usage Examples

### Monitor Repository Health
```bash
curl "http://localhost:8000/metrics/repository-health?repo=microsoft/vscode&hours=168"
```

### Track Developer Productivity
```bash
curl "http://localhost:8000/metrics/developer-productivity?repo=facebook/react&hours=720"
```

### Security Assessment
```bash
curl "http://localhost:8000/metrics/security-monitoring?repo=kubernetes/kubernetes&hours=168"
```

### Anomaly Detection
```bash
curl "http://localhost:8000/metrics/event-anomalies?repo=tensorflow/tensorflow&hours=168"
```

### Release Pipeline Analysis
```bash
curl "http://localhost:8000/metrics/release-deployment?repo=nodejs/node&hours=2160"
```

### Community Health Check
```bash
curl "http://localhost:8000/metrics/community-engagement?repo=python/cpython&hours=168"
```

### Complete Event Overview
```bash
curl "http://localhost:8000/metrics/event-types-summary?repo=golang/go&hours=168"
```

## Integration with MCP

All new monitoring endpoints are also available through the MCP server for AI tool integration:

- `get_repository_health_score(repo_name, hours)`
- `get_developer_productivity_metrics(repo_name, hours)`
- `get_security_monitoring_report(repo_name, hours)`
- `detect_event_anomalies(repo_name, hours)`
- `get_release_deployment_metrics(repo_name, hours)`
- `get_community_engagement_metrics(repo_name, hours)`

## Performance Considerations

- All metrics are computed in real-time from stored events
- Database indexes optimize query performance
- Configurable time windows balance detail vs. performance
- Caching can be implemented for frequently accessed metrics

## Future Enhancements

Potential future additions:
- Machine learning-based anomaly detection
- Predictive analytics for repository health
- Custom alerting and notifications
- Integration with external monitoring systems
- Historical trend analysis and forecasting
- Custom metric definitions and thresholds