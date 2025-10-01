# Commit Monitoring and Change Tracking

## Overview

The GitHub Events Monitor now includes comprehensive commit monitoring and change tracking capabilities. This feature automatically processes PushEvents to capture detailed commit information, analyzes changes, generates summaries, and provides insights into repository activity at the commit level.

## Features

### 🔍 **Automatic Commit Processing**
- Automatically processes PushEvents to extract commit information
- Fetches detailed commit data from GitHub API including file changes
- Stores comprehensive commit metadata and statistics

### 📊 **Intelligent Change Analysis**
- Categorizes commits by type (bugfix, feature, documentation, etc.)
- Calculates impact scores based on changes and file types
- Assesses risk levels and detects breaking changes
- Identifies security-relevant commits

### 📝 **Automated Summaries**
- Generates short and detailed summaries for each commit
- Analyzes commit messages and file changes
- Provides human-readable change descriptions
- Tracks complexity and performance impact

### 🔄 **Multi-Repository Monitoring**
- Monitor commits across multiple repositories
- Cross-repository change tracking
- Aggregated statistics and insights

## Database Schema

### Commits Table
Stores core commit information:
```sql
CREATE TABLE commits (
    sha TEXT PRIMARY KEY,
    repo_name TEXT NOT NULL,
    author_name TEXT,
    author_email TEXT,
    author_login TEXT,
    message TEXT,
    commit_date TEXT,
    branch_name TEXT,
    stats_additions INTEGER,
    stats_deletions INTEGER,
    stats_total_changes INTEGER,
    files_changed INTEGER,
    -- ... additional fields
);
```

### Commit Files Table
Tracks individual file changes:
```sql
CREATE TABLE commit_files (
    commit_sha TEXT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT, -- 'added', 'modified', 'removed', 'renamed'
    additions INTEGER,
    deletions INTEGER,
    patch TEXT, -- The actual diff
    -- ... additional fields
);
```

### Commit Summaries Table
Stores analysis and summaries:
```sql
CREATE TABLE commit_summaries (
    commit_sha TEXT PRIMARY KEY,
    short_summary TEXT,
    detailed_summary TEXT,
    change_categories TEXT, -- JSON array
    impact_score REAL, -- 0-100
    risk_level TEXT, -- 'low', 'medium', 'high'
    breaking_changes BOOLEAN,
    security_relevant BOOLEAN,
    -- ... additional analysis fields
);
```

## API Endpoints

### 1. Recent Commits

Get recent commits for a repository with summaries.

```http
GET /commits/recent?repo={owner}/{repo}&hours={hours}&limit={limit}
```

**Parameters:**
- `repo` (required): Repository name in format "owner/repo"
- `hours` (optional): Hours to look back (default: 24)
- `limit` (optional): Maximum commits to return (default: 50)

**Example Response:**
```json
{
  "repo": "microsoft/vscode",
  "hours": 24,
  "total_commits": 12,
  "commits": [
    {
      "sha": "abc123...",
      "author_name": "John Developer",
      "author_login": "johndeveloper",
      "message": "Fix memory leak in extension host",
      "commit_date": "2025-01-15T10:30:00Z",
      "branch_name": "main",
      "stats": {
        "additions": 15,
        "deletions": 8,
        "total_changes": 23
      },
      "files_changed": 3,
      "summary": {
        "short": "Fix memory leak in extension host",
        "detailed": "Modified 3 files with 15 additions and 8 deletions. Categories: bugfix, performance",
        "categories": ["bugfix", "performance"],
        "impact_score": 45.2,
        "risk_level": "medium",
        "breaking_changes": false,
        "security_relevant": false,
        "performance_impact": "positive"
      }
    }
  ]
}
```

### 2. Repository Change Summary

Get comprehensive change summary for a repository.

```http
GET /commits/summary?repo={owner}/{repo}&hours={hours}
```

**Example Response:**
```json
{
  "repo_name": "microsoft/vscode",
  "analysis_period_hours": 24,
  "statistics": {
    "total_commits": 12,
    "unique_authors": 5,
    "branches_active": 3,
    "total_additions": 245,
    "total_deletions": 89,
    "total_files_changed": 34,
    "avg_commit_size": 27.8
  },
  "quality_metrics": {
    "breaking_changes_count": 0,
    "security_commits_count": 1,
    "high_impact_commits_count": 3,
    "avg_impact_score": 42.5
  },
  "change_categories": {
    "bugfix": 5,
    "feature": 3,
    "documentation": 2,
    "performance": 1,
    "security": 1
  }
}
```

### 3. Commit Details

Get detailed information about a specific commit.

```http
GET /commits/{commit_sha}?repo={owner}/{repo}
```

**Example Response:**
```json
{
  "sha": "abc123...",
  "author_name": "John Developer",
  "message": "Fix memory leak in extension host\n\nThis commit addresses a memory leak that occurred when...",
  "stats": {
    "additions": 15,
    "deletions": 8,
    "total_changes": 23
  },
  "parent_shas": ["def456..."],
  "summary": {
    "impact_score": 45.2,
    "complexity_score": 32.1,
    "categories": ["bugfix", "performance"]
  }
}
```

### 4. Commit File Changes

Get file changes for a specific commit.

```http
GET /commits/{commit_sha}/files?repo={owner}/{repo}
```

**Example Response:**
```json
{
  "commit_sha": "abc123...",
  "repo": "microsoft/vscode",
  "files": [
    {
      "filename": "src/vs/workbench/services/extensions/electron-browser/extensionHost.ts",
      "status": "modified",
      "additions": 12,
      "deletions": 5,
      "changes": 17
    },
    {
      "filename": "src/vs/workbench/test/extensionHost.test.ts",
      "status": "modified",
      "additions": 3,
      "deletions": 3,
      "changes": 6
    }
  ]
}
```

### 5. Multi-Repository Monitoring

Monitor recent commits across multiple repositories.

```http
GET /monitoring/commits?repos={repo1},{repo2},{repo3}&hours={hours}&limit_per_repo={limit}
```

**Parameters:**
- `repos` (required): Comma-separated list of repositories
- `hours` (optional): Hours to look back (default: 24)
- `limit_per_repo` (optional): Max commits per repository (default: 10)

**Example:**
```bash
curl "http://localhost:8000/monitoring/commits?repos=microsoft/vscode,facebook/react,nodejs/node&hours=24&limit_per_repo=5"
```

### 6. Commits by Category

Get commits grouped by change categories.

```http
GET /monitoring/commits/categories?repo={owner}/{repo}&hours={hours}
```

**Example Response:**
```json
{
  "repo": "microsoft/vscode",
  "hours": 24,
  "categories": {
    "bugfix": [
      {
        "sha": "abc123...",
        "message": "Fix memory leak",
        "author_login": "johndeveloper",
        "commit_date": "2025-01-15T10:30:00Z"
      }
    ],
    "feature": [
      {
        "sha": "def456...",
        "message": "Add new debugging features",
        "author_login": "janedeveloper",
        "commit_date": "2025-01-15T09:15:00Z"
      }
    ]
  },
  "total_commits": 12
}
```

### 7. Commits by Author

Get commit statistics grouped by author.

```http
GET /monitoring/commits/authors?repo={owner}/{repo}&hours={hours}
```

**Example Response:**
```json
{
  "repo": "microsoft/vscode",
  "hours": 168,
  "total_authors": 8,
  "authors": [
    {
      "author_login": "johndeveloper",
      "author_name": "John Developer",
      "commit_count": 15,
      "total_additions": 245,
      "total_deletions": 89,
      "total_files_changed": 34,
      "avg_impact_score": 52.3,
      "breaking_commits": 0,
      "security_commits": 1
    }
  ]
}
```

### 8. High-Impact Commits

Get high-impact commits for a repository.

```http
GET /monitoring/commits/impact?repo={owner}/{repo}&hours={hours}&min_impact_score={score}
```

**Parameters:**
- `min_impact_score` (optional): Minimum impact score (default: 70.0)

## Change Categories

Commits are automatically categorized based on commit messages and file changes:

- **bugfix** - Bug fixes and error corrections
- **feature** - New features and functionality
- **refactor** - Code refactoring and cleanup
- **documentation** - Documentation updates
- **testing** - Test additions and modifications
- **performance** - Performance improvements
- **security** - Security-related changes
- **breaking** - Breaking changes
- **configuration** - Configuration file changes
- **database** - Database schema and migration changes
- **infrastructure** - Docker, CI/CD, deployment changes

## Impact Scoring

Commits receive impact scores (0-100) based on:

- **Change Volume** (0-50 points): Number of additions/deletions
- **File Count** (0-30 points): Number of files modified
- **Critical Files** (0-20 points): Changes to important files (package.json, Dockerfile, etc.)

**Impact Levels:**
- **Low** (0-39): Small changes, minor updates
- **Medium** (40-69): Moderate changes, typical features/fixes
- **High** (70-100): Large changes, major features, architectural changes

## Risk Assessment

Commits are assessed for risk level:

- **High Risk**: Breaking changes, security issues, large changes (>500 lines or >20 files)
- **Medium Risk**: Moderate changes (100-500 lines or 5-20 files)
- **Low Risk**: Small changes (<100 lines or <5 files)

## Usage Examples

### Monitor Your Repositories

```bash
# Get recent commits for your main repository
curl "http://localhost:8000/commits/recent?repo=myorg/myapp&hours=24"

# Get change summary for the last week
curl "http://localhost:8000/commits/summary?repo=myorg/myapp&hours=168"

# Monitor multiple repositories
curl "http://localhost:8000/monitoring/commits?repos=myorg/frontend,myorg/backend,myorg/api&hours=24"
```

### Track Specific Changes

```bash
# Get details for a specific commit
curl "http://localhost:8000/commits/abc123def456?repo=myorg/myapp"

# See what files were changed
curl "http://localhost:8000/commits/abc123def456/files?repo=myorg/myapp"

# Find high-impact commits
curl "http://localhost:8000/monitoring/commits/impact?repo=myorg/myapp&min_impact_score=80"
```

### Analyze Development Patterns

```bash
# See commits by category
curl "http://localhost:8000/monitoring/commits/categories?repo=myorg/myapp&hours=168"

# Track author contributions
curl "http://localhost:8000/monitoring/commits/authors?repo=myorg/myapp&hours=720"
```

## MCP Integration

All commit monitoring features are available through MCP tools:

```python
# Available MCP tools for commit monitoring
get_recent_commits(repo_name, hours=24, limit=50)
get_repository_change_summary(repo_name, hours=24)
get_commit_details(commit_sha, repo_name)
get_high_impact_commits(repo_name, hours=168, min_impact_score=70.0)
monitor_multiple_repositories(repos_list, hours=24)
```

**Example MCP Usage:**
```
"Show me recent commits for microsoft/vscode in the last 24 hours"
"What are the high-impact commits in kubernetes/kubernetes this week?"
"Give me a change summary for tensorflow/tensorflow"
"Monitor commits across my repositories: myorg/frontend,myorg/backend"
```

## Automated Processing

The system automatically:

1. **Detects PushEvents** from the GitHub Events API
2. **Fetches Commit Details** using GitHub's Commits API
3. **Analyzes Changes** including file modifications and statistics
4. **Generates Summaries** with categorization and impact scoring
5. **Stores Everything** in the local database for fast querying

## Performance Considerations

- **Rate Limiting**: Respects GitHub API rate limits when fetching commit details
- **Deduplication**: Avoids processing the same commit multiple times
- **Batch Processing**: Processes commits efficiently during event collection
- **Indexed Queries**: Database indexes optimize query performance

## Configuration

Set environment variables to configure commit monitoring:

```bash
# GitHub token for higher API rate limits (recommended)
export GITHUB_TOKEN="your_github_token_here"

# Target repositories to monitor (optional)
export TARGET_REPOSITORIES="owner/repo1,owner/repo2"

# Database path
export DATABASE_PATH="./github_events.db"
```

## Benefits

### For Developers
- **Change Visibility**: See exactly what changed and when
- **Impact Assessment**: Understand the scope of changes
- **Quality Tracking**: Monitor code quality trends

### For Team Leads
- **Team Activity**: Track developer contributions and patterns
- **Risk Management**: Identify high-risk changes early
- **Process Insights**: Understand development workflows

### For DevOps Teams
- **Deployment Planning**: Assess change impact before deployment
- **Rollback Planning**: Identify changes that might need rollback
- **Release Notes**: Auto-generate release notes from commit summaries

### For Security Teams
- **Security Monitoring**: Track security-relevant changes
- **Compliance**: Monitor for breaking changes and policy violations
- **Audit Trail**: Comprehensive change tracking for audits

## Future Enhancements

Planned improvements include:
- **AI-Enhanced Summaries**: More intelligent change analysis
- **Custom Categories**: User-defined change categories
- **Alerting**: Notifications for high-impact or risky commits
- **Visualization**: Charts and graphs of commit patterns
- **Integration**: Webhook support for real-time notifications