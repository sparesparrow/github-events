# GitHub Events Monitor

A comprehensive Python-based service that monitors **23 different GitHub event types** and provides advanced repository analytics. Features include repository health scoring, developer productivity analysis, security monitoring, anomaly detection, community engagement metrics, and detailed commit tracking with automated summaries. Supports both SQLite and AWS DynamoDB backends.

## Architecture (C4 L1)

[Person: Dashboard User] → [Container: GitHub Pages (docs/)] ← [Container: Data Exporter] ← [Container: Events DB (SQLite)] ← [Container: Event Monitor Service] ← [External System: GitHub API /events]
[Person: API Consumer] → [Container: MCP Server] → [Container: Events DB (SQLite)]

```mermaid
graph LR
  user["Person: User"] -->|HTTP/JSON| api["Container: REST API Service\n(FastAPI - metrics & viz)"]
  api <--> |HTTP (GitHub REST)| gh["External System: GitHub REST API (/events)"]
  api <--> |SQL (aiosqlite)| db["Container: Database (SQLite)\n(Persist events, query metrics)"]
```

## Components

- **Enhanced Event Monitor**: Monitors 23+ GitHub event types including development, collaboration, security, and deployment events
  - Comprehensive event filtering and processing
  - Advanced metrics calculation and health scoring
  - Anomaly detection and pattern analysis
- **Advanced Analytics Engine**: Repository health, developer productivity, security monitoring, and community engagement analysis
- **MCP Server**: Enhanced tools for AI integration with comprehensive monitoring capabilities
- **REST API**: 15+ endpoints for metrics, analytics, and monitoring
- **Data Exporter**: Builds docs/data.json and interactive visualizations
- **GitHub Pages**: Static dashboard with live API integration
- **🆕 Ecosystem Monitoring System**: Multi-domain monitoring with cross-domain cooperation
  - Scheduled aggregation every 4 hours across multiple domains
  - Advanced failure analysis with domain-specific pattern detection
  - Automated stale detection and cleanup for PRs and branches
  - Cross-domain cooperation via repository dispatch and workflow dispatch
  - Comprehensive alerting and notification system

## Configuration

The service can be configured via environment variables:

### Core Configuration
- `TARGET_REPOSITORIES`: Comma-separated list of repositories to monitor (e.g., "owner/repo1,owner/repo2")
- `GITHUB_TOKEN`: GitHub personal access token for higher API rate limits
- `POLL_INTERVAL`: Polling interval in seconds (default: 300)

### Database Configuration
- `DATABASE_PROVIDER`: Database backend - "sqlite" or "dynamodb" (default: sqlite)

#### SQLite Configuration (DATABASE_PROVIDER=sqlite)
- `DATABASE_PATH`: Path to SQLite database file (default: ./github_events.db)

#### DynamoDB Configuration (DATABASE_PROVIDER=dynamodb)
- `AWS_REGION`: AWS region (default: us-east-1)
- `DYNAMODB_TABLE_PREFIX`: Table name prefix (default: github-events-)
- `DYNAMODB_ENDPOINT_URL`: Custom endpoint for local DynamoDB
- `AWS_ACCESS_KEY_ID`: AWS access key (optional if using IAM roles)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (optional if using IAM roles)

## 🚀 Quick Start - Live Dashboard

### Option 1: One-Command Live Dashboard
```bash
./start-live-dashboard.sh
```
This script will:
- Set up the environment
- Start the API server 
- Open the live dashboard in your browser
- Show real-time GitHub Events data

### Option 2: Manual Setup

1) **Python Environment**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) **Choose Database Provider**
```bash
# Option A: SQLite (default, for development)
export DATABASE_PROVIDER=sqlite
export DATABASE_PATH=./github_events.db

# Option B: DynamoDB (for production scale)
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-west-2
python scripts/setup_dynamodb.py create
```

3) **Start API Server**
```bash
export GITHUB_TOKEN="your_github_token"  # optional, for higher rate limits
export CORS_ORIGINS="*"  # enable CORS for dashboard
python -m src.github_events_monitor.enhanced_api
```

4) **Open Live Dashboard**
- Open `docs/index.html` in your browser
- Dashboard automatically connects to `http://localhost:8000`
- **Real-time data** refreshes every 30 seconds
- Fallback to static files if API unavailable

### 📊 Dashboard Features
- **🔴 Live API Data**: Real-time metrics from running API server
- **📁 Static Fallback**: Works with pre-generated JSON files  
- **🔧 Configurable**: Edit `docs/config.js` to change API endpoints
- **📱 Responsive**: Mobile-friendly design with interactive charts
- **🔄 Auto-refresh**: Live updates every 30 seconds
- **🐛 Debug Console**: Real-time connection and data status

## 📚 Complete Installation & Usage Guide

### 🛠️ Installation Methods

#### Method 1: pip install (Recommended)
```bash
# Clone repository
git clone https://github.com/sparesparrow/github-events-clone.git
cd github-events-clone

# Install with pip
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt
```

#### Method 2: uv (Ultra-fast Python package manager)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies with uv
uv pip install -r requirements.txt

# Or install the package in development mode
uv pip install -e .
```

#### Method 3: Docker
```bash
# Build and run with Docker Compose
cd ./
docker-compose up -d

# Or build manually
docker build -t github-events-monitor .
docker run -p 8000:8000 -e GITHUB_TOKEN=your_token github-events-monitor
```

### 🔧 Environment Configuration

Create a `.env` file in the project root:
```bash
# Required for higher API rate limits
GITHUB_TOKEN=ghp_your_personal_access_token_here

# Optional: Monitor specific repositories
TARGET_REPOSITORIES=owner/repo1,owner/repo2,owner/repo3

# Database configuration
DATABASE_PATH=./github_events.db

# API server settings
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=*

# Polling interval (seconds)
POLL_INTERVAL=300
```

### 🌐 Web Application Usage

#### Starting the API Server
```bash
# Method 1: Using the module
python -m src.github_events_monitor.api

# Method 2: Using the installed script (if installed with pip)
github-events-monitor-api

# Method 3: With custom configuration
GITHUB_TOKEN=your_token DATABASE_PATH=./custom.db python -m src.github_events_monitor.api
```

#### Accessing the Dashboard
1. **Local HTML Dashboard**: Open `docs/index.html` in your browser
2. **API Documentation**: Visit `http://localhost:8000/docs`
3. **Health Check**: Visit `http://localhost:8000/health`

#### REST API Endpoints
- **Health**: `GET /health`
- **Event Counts**: `GET /metrics/event-counts?offset_minutes=60`
- **PR Intervals**: `GET /metrics/pr-interval?repo=owner/repo`
- **Repository Activity**: `GET /metrics/repository-activity?repo=owner/repo&hours=24`
- **Trending Repos**: `GET /metrics/trending?hours=24&limit=10`
- **Visualization**: `GET /visualization/trending-chart?hours=24&limit=5&format=png`

### 🔌 MCP Client Usage

#### Starting the MCP Server
```bash
# Method 1: Run the MCP server script (recommended)
python scripts/mcp_server.py

# Method 2: Custom database path
DATABASE_PATH=./custom.db python scripts/mcp_server.py
```

#### MCP Client Configuration

**For Cursor IDE** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "github-events": {
      "command": "python",
      "args": [
        "scripts/mcp_server.py"
      ],
      "cwd": "/path/to/github-events-clone",
      "env": {
        "DATABASE_PATH": "./github_events.db",
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

**For Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "github-events": {
      "command": "python",
      "args": [
        "-m", "src.github_events_monitor.mcp_server"
      ],
      "cwd": "/path/to/github-events-clone",
      "env": {
        "DATABASE_PATH": "./github_events.db"
      }
    }
  }
}
```

#### Available MCP Tools
- `get_event_counts(offset_minutes)`: Get event counts by type
- `get_avg_pr_interval(repo_name)`: Average time between PR events
- `get_repository_activity(repo_name, hours)`: Activity summary for repository
- `get_trending_repositories(hours, limit)`: Most active repositories
- `get_trending_chart_image(hours, limit, format)`: Generate trending chart
- `get_pr_timeline_chart(repo_name, days, format)`: PR timeline visualization
- `collect_events_now(limit)`: Trigger manual event collection
- `get_health()`: Service health status

Additional DB-backed tools (direct SQLite access via MCP server):
- `db_get_average_pr_time(repo_name)`
- `db_get_events_by_offset(offset_minutes)`
- `db_get_repository_activity(repo_name, limit)`
- `db_get_top_repositories(limit)`
- `db_get_event_statistics()`

### 🌊 curl Command Examples

#### Health Check
```bash
curl -X GET "http://localhost:8000/health" \
  -H "accept: application/json"
```

#### Get Event Counts (Last Hour)
```bash
curl -X GET "http://localhost:8000/metrics/event-counts?offset_minutes=60" \
  -H "accept: application/json"
```

#### Get Event Counts (camelCase alias)
```bash
curl -X GET "http://localhost:8000/metrics/event-counts?offsetMinutes=60" \
  -H "accept: application/json"
```

#### Get Repository Activity
```bash
curl -X GET "http://localhost:8000/metrics/repository-activity?repo=microsoft/vscode&hours=24" \
  -H "accept: application/json"
```

#### Get Trending Repositories
```bash
curl -X GET "http://localhost:8000/metrics/trending?hours=24&limit=10" \
  -H "accept: application/json"
```

#### Get Event Counts Timeseries (JSON)
```bash
curl -X GET "http://localhost:8000/metrics/event-counts-timeseries?hours=6&bucket_minutes=5" \
  -H "accept: application/json"
```

#### Get Event Counts Timeseries (repo)
```bash
curl -X GET "http://localhost:8000/metrics/event-counts-timeseries?hours=12&bucket_minutes=15&repo=owner/repo" \
  -H "accept: application/json"
```

#### Events Timeseries Chart (PNG)
```bash
curl -X GET "http://localhost:8000/visualization/event-counts-timeseries?hours=24&bucket_minutes=5&format=png" \
  -H "accept: image/png" \
  --output events_timeseries.png
```

#### Average PR Interval (alias route)
```bash
curl -X GET "http://localhost:8000/metrics/avg-pr-interval?repo=owner/repo" \
  -H "accept: application/json"
```

#### Generate Trending Chart (PNG)
```bash
curl -X GET "http://localhost:8000/visualization/trending-chart?hours=24&limit=5&format=png" \
  -H "accept: image/png" \
  --output trending_chart.png
```

#### Trigger Manual Collection
```bash
curl -X POST "http://localhost:8000/collect?limit=100" \
  -H "accept: application/json"
```

#### Webhook for GitHub Events
```bash
curl -X POST "http://localhost:8000/webhook" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: watch" \
  -d '{
    "action": "started",
    "repository": {
      "full_name": "owner/repo",
      "stargazers_count": 100
    }
  }'
```

### 🌐 Ecosystem Monitoring System

### Multi-Domain Monitoring

The system now includes comprehensive ecosystem monitoring capabilities for managing multiple GitHub domains:

**Key Features**:
- **Scheduled Monitoring**: Every 4 hours, monitors multiple domains for events and failures
- **Failure Analysis**: Advanced log analysis with domain-specific pattern detection (Conan, FIPS, workflow errors)
- **Stale Detection**: Automated detection and management of stale PRs and branches
- **Cross-Domain Cooperation**: Repository dispatch events, workflow dispatch, and artifact sharing
- **Alerting**: Automated issue creation and notifications with configurable thresholds

**Monitored Domains**:
- `openssl-tools`
- `openssl-conan-base`
- `openssl-fips-policy`
- `mcp-project-orchestrator`

**Workflows**:
- **Ecosystem Monitor**: `.github/workflows/monitor-ecosystem.yml` - Main monitoring workflow
- **Stale Detection**: `.github/workflows/stale-detection.yml` - Automated stale item management

**Scripts**:
- **Ecosystem Monitor**: `scripts/ecosystem_monitor.py` - Multi-domain event collection and analysis
- **Enhanced Fixer**: `scripts/fixer.py` - Log analysis and workflow fix suggestions
- **Stale Detector**: `scripts/stale_detector.py` - Stale PR and branch detection
- **Alert Manager**: `scripts/alert_manager.py` - Alert creation and cross-domain notifications

### Quick Start - Ecosystem Monitoring

```bash
# Run ecosystem monitoring manually
gh workflow run monitor-ecosystem.yml \
  -f domains="openssl-tools,openssl-conan-base" \
  -f force_run=true

# Check for stale items
gh workflow run stale-detection.yml \
  -f dry_run=true \
  -f days_until_stale=30

# Analyze logs and generate fixes
python scripts/fixer.py \
  --log-files "build.log" "test.log" \
  --cooperation \
  --target-repos "sparesparrow/github-events"
```

### Alert Thresholds

- **Health Score**: 80+ (Healthy), 60-79 (Warning), 0-59 (Critical)
- **Stale Threshold**: 30 days without activity
- **Cleanup Threshold**: 7 days after stale detection
- **Activity Threshold**: Events in last 4 hours

### Cross-Domain Cooperation

- **Repository Dispatch**: Trigger workflows in other repositories
- **Workflow Dispatch**: Manual orchestration across domains
- **Artifact Sharing**: Cloudsmith integration with OIDC authentication
- **Issue Creation**: Automated alerts and notifications

For detailed documentation, see **[docs/ECOSYSTEM_MONITORING.md](docs/ECOSYSTEM_MONITORING.md)**.

## ☁️ AWS Integration

#### S3 Static Website Deployment

1. **Create S3 Bucket**:
```bash
aws s3 mb s3://your-github-events-dashboard
aws s3 website s3://your-github-events-dashboard \
  --index-document index.html \
  --error-document error.html
```

2. **Set Bucket Policy** (replace `your-github-events-dashboard`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-github-events-dashboard/*"
    }
  ]
}
```

3. **Deploy Using GitHub Actions**:
Set these secrets in your GitHub repository:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Then trigger the AWS deployment workflow:
```bash
# Via GitHub UI: Actions → "Deploy static dashboard to AWS S3" → Run workflow
# Or via gh CLI:
gh workflow run aws_deploy.yml \
  -f s3_bucket=your-github-events-dashboard \
  -f aws_region=us-east-1 \
  -f cloudfront_distribution_id=E1234567890
```

#### EC2 Deployment

**User Data Script** for EC2 instance:
```bash
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git

# Clone and setup
cd /opt
git clone https://github.com/sparesparrow/github-events-clone.git
cd github-events-clone
pip3 install -r requirements.txt

# Create systemd service
cat > /etc/systemd/system/github-events.service << EOF
[Unit]
Description=GitHub Events Monitor API
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/github-events-clone
Environment=GITHUB_TOKEN=your_token_here
Environment=API_HOST=0.0.0.0
Environment=API_PORT=8000
ExecStart=/usr/bin/python3 -m src.github_events_monitor.api
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable github-events
systemctl start github-events
```

#### Lambda Deployment

**Serverless API with AWS Lambda**:
```python
# lambda_function.py
import json
from mangum import Mangum
from src.github_events_monitor.api import app

handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    return handler(event, context)
```

**Deploy with SAM**:
```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  GitHubEventsAPI:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./
      Handler: lambda_function.lambda_handler
      Runtime: python3.11
      Environment:
        Variables:
          GITHUB_TOKEN: !Ref GitHubToken
      Events:
        ApiGateway:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY

Parameters:
  GitHubToken:
    Type: String
    NoEcho: true
```

#### RDS Integration

**Environment variables for PostgreSQL**:
```bash
export DATABASE_URL="postgresql://username:password@rds-endpoint:5432/github_events"
export DATABASE_PATH=""  # Leave empty to use DATABASE_URL
```

**CloudFormation RDS setup**:
```yaml
GitHubEventsDB:
  Type: AWS::RDS::DBInstance
  Properties:
    DBInstanceIdentifier: github-events-db
    DBInstanceClass: db.t3.micro
    Engine: postgres
    EngineVersion: '15.4'
    MasterUsername: github_events
    MasterUserPassword: !Ref DBPassword
    AllocatedStorage: '20'
    VPCSecurityGroups:
      - !Ref DatabaseSecurityGroup
```

### 🔄 CI/CD Integration

#### GitHub Actions Secrets Required
```bash
# GitHub repository secrets
GITHUB_TOKEN          # For API access
AWS_ACCESS_KEY_ID     # For S3 deployment
AWS_SECRET_ACCESS_KEY # For S3 deployment
```

#### Custom Deployment Script
```bash
#!/bin/bash
# deploy.sh - Custom deployment script

set -e

echo "🚀 Deploying GitHub Events Monitor..."

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "
import asyncio
from src.github_events_monitor.event_collector import GitHubEventsCollector

async def init():
    collector = GitHubEventsCollector('github_events.db', '$GITHUB_TOKEN')
    await collector.initialize_database()
    print('✅ Database initialized')

asyncio.run(init())
"

# Start API server
echo "🌐 Starting API server..."
python -m src.github_events_monitor.api &
API_PID=$!

# Wait for health check
echo "⏳ Waiting for API to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ API is healthy"
        break
    fi
    sleep 2
done

echo "🎉 Deployment complete!"
echo "📊 Dashboard: http://localhost:8000/docs"
echo "🔍 Health: http://localhost:8000/health"
```

#### Automated Database Updates

The project includes a **scheduled GitHub Actions workflow** that automatically updates the GitHub events database:

**Workflow**: `.github/workflows/update-events-db.yml`
- **Schedule**: Runs every hour (`cron: '0 * * * *'`)
- **Manual Trigger**: Can be triggered manually via GitHub Actions UI
- **Docker-based**: Uses the project's Dockerfile for consistent execution
- **Artifact**: Uploads the updated database as a workflow artifact

**Key Features**:
- ✅ **Docker-based execution** - Uses the working Dockerfile for reliability
- ✅ **Fixed pyproject.toml** - Resolved TOML parsing issues
- ✅ **Volume mounting** - Persists database between container runs
- ✅ **Environment variables** - Properly passes GitHub token and database path
- ✅ **Error handling** - Robust execution with proper error reporting

**Recent Fixes**:
- Fixed duplicate `[project]` sections in `pyproject.toml`
- Updated workflow to use Docker instead of direct Python installation
- Improved database path handling for containerized execution

```mermaid
flowchart TD

%% People
A["Person: Dashboard User"]:::person
B["Person: API Consumer"]:::person
C["Person: MCP Client"]:::person

%% External actors/systems
MR["Actor: MonitoredRepo (owner/repo)"]:::repo
G["External System: GitHub API (/events)"]:::external

%% New external actor: MCP Server as tool provider
MS["Actor: MCP Server (Tool Provider)"]:::actorTool

%% External/configured database actor (variants)
subgraph DBA["Actor: Database (external/configured)"]
  direction TB
  DBF["File: github-events.db"]:::db
  DBU["URL: postgresql://…  |  sqlite:///…"]:::db
end

%% System boundary
subgraph S["Software System: GitHub Events Monitor"]
  direction TB
  subgraph Ctrs["Containers"]
    E["Container: Event Monitor Service\n(Polls /events; filters WatchEvent, PullRequestEvent, IssuesEvent)"]
    D["Container: Events DB (SQLite)"]
    F["Container: FastAPI REST API\n(health, metrics, visualization endpoints)"]
    M["Container: MCP Server\n(tools expose DB-backed metrics & exporters)"]
    X["Container: Data Exporter\n(writes JSON and charts to docs/)"]
    P["Container: GitHub Pages (docs/)\n(static dashboard)"]
  end

  %% Generic Tool abstraction (REST + MCP)
  subgraph TSG["Generic Tool Abstraction"]
    direction TB
    T["Generic Tool (Metrics & Viz)"]:::tool

    %% REST endpoints
    subgraph RE["REST Endpoints"]
      direction TB
      H1["GET /health"]:::endpoint
      E2["GET /metrics/event-counts?offset_minutes=60"]:::endpoint
      E1["GET /metrics/pr-interval?repo=owner/repo"]:::endpoint
      E5["GET /metrics/repository-activity?repo=owner/repo&hours=24"]:::endpoint
      E6["GET /metrics/trending?hours=24&limit=10"]:::endpoint
      V1["GET /visualization/trending-chart?hours=24&limit=5&format=png"]:::endpoint
      DOCS["OpenAPI Docs: /docs"]:::endpoint
    end

    %% MCP tools (conceptual operations)
    subgraph MT["MCP Tools"]
      direction TB
      MT1["tool: pr_interval"]:::endpoint
      MT2["tool: event_counts"]:::endpoint
      MT3["tool: trending_chart"]:::endpoint
      MT4["tool: pr_timeline"]:::endpoint
    end
  end
end

%% People interactions
A -->|Views dashboards| P
B -->|HTTP requests| F
C -->|Invokes tools| MS

%% Event flow to GitHub
MR -->|Emits: WatchEvent / PullRequestEvent / IssuesEvent| G
E -->|GET /events| G

%% Internal DB path
E -->|writes| D
F -->|SQL reads| D
M -->|SQL reads/tools| D
X -->|reads metrics| D
X -->|publishes| P

%% External/configured DB options (optional)
F -.->|alt: reads via DATABASE_URL| DBU
M -.->|alt: read-only via MCP Postgres| DBU
E -.->|alt: writes to configured DB| DBU
X -.->|alt: reads/writes| DBU

%% File-based external usage (optional)
F -.->|alt: reads file| DBF
M -.->|alt: reads file| DBF

%% Tool provider behavior: tools proxy to REST endpoints
MS -->|provides| MT1
MS -->|provides| MT2
MS -->|provides| MT3
MS -->|provides| MT4

%% HTTP calls from MCP Server to REST endpoints
MS -->|executes HTTP curl| H1
MS -->|executes HTTP curl| E2
MS -->|executes HTTP curl| E1
MS -->|executes HTTP curl| E5
MS -->|executes HTTP curl| E6
MS -->|executes HTTP curl| V1

%% Show implementation relation to internal MCP container
MS -.->|implemented by this repo| M

%% API wiring for completeness
F -->|exposes| H1
F -->|exposes| E2
F -->|exposes| E1
F -->|exposes| E5
F -->|exposes| E6
F -->|exposes| V1
F -->|exposes| DOCS

B -->|calls| H1
B -->|calls| E2
B -->|calls| E1
B -->|calls| E5
B -->|calls| E6
B -->|opens| DOCS

%% Styles
classDef person fill:#f6f9ff,stroke:#5b8def,stroke-width:1px,color:#1b3a70;
classDef external fill:#fff7e6,stroke:#f0b429,stroke-width:1px,color:#5a3a00;
classDef actorTool fill:#f4ffef,stroke:#2ecc71,stroke-width:1px,color:#114d2e;
classDef tool fill:#eefbf2,stroke:#2ecc71,stroke-width:1px,color:#114d2e;
classDef endpoint fill:#ffffff,stroke:#bbbbbb,stroke-width:1px,color:#333333;
classDef repo fill:#fff0f6,stroke:#d6336c,stroke-width:1px,color:#7a1f3b;
classDef db fill:#eef2ff,stroke:#4c6ef5,stroke-width:1px,color:#243972;
```
```mermaid
flowchart TB

%% People (stacked to reduce width)
A["Person: Dashboard User"]:::person
B["Person: API Consumer"]:::person
C["Person: MCP Client"]:::person

%% External actors/systems (stacked)
MR["Actor: MonitoredRepo (owner/repo)"]:::repo
G["External System: GitHub API (/events)"]:::external

%% Tool provider actor (stacked)
MS["Actor: MCP Server (Tool Provider)"]:::actorTool

%% Database variants (stacked at bottom to avoid width)
subgraph DBA["Actor: Database (external/configured)"]
  direction TB
  DBF["File: github-events.db"]:::db
  DBU["URL: postgresql://…\nsqlite:///…"]:::db
end

%% System boundary (make interior vertical)
subgraph S["Software System: GitHub Events Monitor"]
  direction TB

  %% Containers stacked to keep narrow
  E["Container: Event Monitor Service\n(Polls /events; filters Watch, PR, Issues)"]:::internal
  D["Container: Events DB (SQLite)"]:::internal
  F["Container: FastAPI REST API\n(health, metrics, visualization)"]:::internal
  M["Container: MCP Server\n(DB-backed tools & exporters)"]:::internal
  X["Container: Data Exporter\n(writes JSON & charts to docs/)"]:::internal
  P["Container: GitHub Pages (docs/)\n(static dashboard)"]:::internal

  %% Collapsed endpoint list (multiline) to reduce width
  EP["REST Endpoints\n- GET /health\n- GET /metrics/event-counts?offset_minutes=60\n- GET /metrics/pr-interval?repo=owner/repo\n- GET /metrics/repository-activity?repo=owner/repo&hours=24\n- GET /metrics/trending?hours=24&limit=10\n- GET /visualization/trending-chart?hours=24&limit=5&format=png\n- OpenAPI: /docs"]:::endpoint

  %% Collapsed MCP tools list (conceptual) to reduce width
  MT["MCP Tools\n- tool: pr_interval\n- tool: event_counts\n- tool: trending_chart\n- tool: pr_timeline\n- tool: export_dashboard_html"]:::endpoint
end

%% People interactions
A -->|Views dashboards| P
B -->|HTTP requests| F
C -->|Invokes tools| MS

%% Event flow (kept vertical)
MR -->|Emits: Watch / PR / Issues| G
E -->|GET /events| G

%% Internal DB path (vertical)
E -->|writes| D
F -->|SQL reads| D
M -->|SQL reads/tools| D
X -->|reads metrics| D
X -->|publishes| P

%% Compact wiring for endpoints/tools
F -->|exposes| EP
M -->|provides| MT

%% Single proxy edge (reduces lateral fan-out)
MS -->|HTTP proxy for endpoints| F

%% Show implementation relation (dashed, vertical)
MS -.->|implemented by this repo| M

%% External/configured DB options (optional; placed at bottom to avoid width)
F -.->|alt: reads via DATABASE_URL| DBU
M -.->|alt: read-only via MCP Postgres| DBU
E -.->|alt: writes to configured DB| DBU
X -.->|alt: reads/writes| DBU
F -.->|alt: reads file| DBF
M -.->|alt: reads file| DBF

%% Styles
classDef person fill:#f6f9ff,stroke:#5b8def,stroke-width:1px,color:#1b3a70;
classDef external fill:#fff7e6,stroke:#f0b429,stroke-width:1px,color:#5a3a00;
classDef internal fill:#eefbf2,stroke:#2ecc71,stroke-width:1px,color:#114d2e;

```
```mermaid
flowchart TB
  %% Title: System Context diagram for GitHub Events Monitor

  %% People (actors)
  person_dashboard["Person: Dashboard User\nViews published dashboards"]:::person
  person_api["Person: API Consumer\nCalls REST API for metrics"]:::person
  person_mcp["Person: MCP Client\nInvokes tools exposed by MCP server"]:::person

  %% Software system in scope
  system_main["Software System: GitHub Events Monitor\nCollects GitHub events, stores data, exposes metrics, and publishes dashboards"]:::system

  %% External software systems
  ext_github_api["Software System: GitHub API (/events)\nPublic events stream"]:::external
  ext_repo["Software System: Monitored Repo (owner/repo)\nEmits Watch/PullRequest/Issues events"]:::external
  ext_hosting["Software System: Static Hosting (GitHub Pages / S3)\nServes static dashboard from docs/"]:::external
  ext_db["Software System: External Database (DATABASE_URL)\nOptional Postgres/SQLite via URL"]:::external

  %% Relationships
  person_dashboard -->|"Views dashboard"| ext_hosting
  person_api -->|"Calls metrics/visualization endpoints"| system_main
  person_mcp -->|"Uses MCP tools (proxies to metrics/visualization)"| system_main

  system_main -->|"Publishes static dashboard artifacts"| ext_hosting
  system_main -->|"Polls public events"| ext_github_api
  ext_repo -->|"Emits events consumed via /events"| ext_github_api

  %% Optional external DB in addition to internal SQLite
  system_main -.->|"Optional read/write via DATABASE_URL"| ext_db

  %% Styles
  classDef person fill:#f6f9ff,stroke:#5b8def,stroke-width:1px,color:#1b3a70;
  classDef system fill:#eefbf2,stroke:#2ecc71,stroke-width:1px,color:#114d2e;
  classDef external fill:#fff7e6,stroke:#f0b429,stroke-width:1px,color:#5a3a00;

```

```mermaid
flowchart TD

%% People
person_dashboard["Person: Dashboard User"]:::person
person_api["Person: API Consumer"]:::person
person_mcp["Person: MCP Client"]:::person

%% External systems
ext_repo["Software System: Monitored Repo (owner/repo)\nEmits Watch/PullRequest/Issues events"]:::external
ext_github_api["Software System: GitHub API (/events)\nPublic events stream"]:::external
ext_pages["Software System: Static Hosting (GitHub Pages/S3)\nServes docs/ dashboard"]:::external
ext_db["Software System: External Database (DATABASE_URL)\nPostgres/SQLite via URL (optional)"]:::external

%% System in scope
subgraph system["Software System: GitHub Events Monitor"]
  em["Container: Event Monitor Service\nPython (poller, GitHub client, filter)\nResponsibility: fetch & persist events"]:::internal
  api["Container: REST API\nPython FastAPI/Uvicorn\nResponsibility: health, metrics, visualization"]:::internal
  mcp["Container: MCP Server\nPython (tools map to API)\nResponsibility: tool-based access to metrics/viz"]:::internal
  db["Container: Events DB\nSQLite file (events.db)\nResponsibility: store events & metrics inputs"]:::internal
  exporter["Container: Data Exporter\nPython/Plotly\nResponsibility: write JSON + charts to docs/"]:::internal
  pages["Container: GitHub Pages Site\nStatic HTML/JS in docs/\nResponsibility: publish dashboard"]:::internal
end

%% People interactions
person_dashboard -->|"Views dashboards"| pages
person_api -->|"Calls REST endpoints"| api
person_mcp -->|"Invokes tools"| mcp

%% Event ingestion
ext_repo -->|"Emits events"| ext_github_api
em -->|"Polls /events (HTTP)"| ext_github_api

%% Internal data flows
em -->|"Writes events"| db
api -->|"Reads metrics data (SQL)"| db
mcp -->|"Reads metrics data (SQL)"| db
exporter -->|"Reads metrics data (SQL)"| db
exporter -->|"Publishes static data & charts"| pages

%% Optional external DB
api -.->|"Alt: read via DATABASE_URL (SQL)"| ext_db
mcp -.->|"Alt: read-only via MCP Postgres"| ext_db
em -.->|"Alt: write to configured DB"| ext_db
exporter -.->|"Alt: read for export"| ext_db

%% Styles
classDef person fill:#f6f9ff,stroke:#5b8def,stroke-width:1px,color:#1b3a70;
classDef external fill:#fff7e6,stroke:#f0b429,stroke-width:1px,color:#5a3a00;
classDef internal fill:#eefbf2,stroke:#2ecc71,stroke-width:1px,color:#114d2e;
```

```mermaid
flowchart TD

%% Container boundary
subgraph api["Container: REST API (FastAPI/Uvicorn)"]
  direction TB

  %% Endpoints / Controllers
  endpoints["Component: ApiEndpoint classes\n- Health, Metrics, Visualization\n- Collect & Webhook\n- MCP capabilities/tools/resources/prompts"]:::comp

  %% Services
  metrics_svc["Component: MetricsService"]:::comp
  viz_svc["Component: VisualizationService"]:::comp
  health_svc["Component: HealthReporter"]:::comp

  %% Repository / DAO / DB access
  repo["Component: EventsRepository"]:::comp
  dao_factory["Component: EventsDaoFactory"]:::comp
  daos["Component: EventsDao + (Watch/PR/Issues) DAOs"]:::comp
  db_pool["Component: DB Connection (aiosqlite)"]:::comp
end

%% External/Internal dependencies
db["Container: Events DB (SQLite)"]:::store

%% Wiring
endpoints --> metrics_svc
endpoints --> viz_svc
endpoints --> health_svc
metrics_svc --> repo
viz_svc --> repo
repo --> dao_factory
dao_factory --> daos
daos --> db_pool
db_pool --> db

%% Styles
classDef comp fill:#ffffff,stroke:#888,stroke-width:1px,color:#333;
classDef store fill:#eef2ff,stroke:#4c6ef5,stroke-width:1px,color:#243972;

```

```mermaid
classDiagram
direction TB

class ApiEndpoint {
  +path: str
  +method: str
  +name: str
  +summary: str
  +register(target)
}

class HealthEndpoint
class MetricsEventCountsEndpoint
class MetricsPrIntervalEndpoint
class MetricsRepositoryActivityEndpoint
class MetricsTrendingEndpoint
class VisualizationTrendingChartEndpoint
class VisualizationPrTimelineEndpoint
class CollectEndpoint
class WebhookEndpoint
class McpCapabilitiesEndpoint
class McpToolsEndpoint
class McpResourcesEndpoint
class McpPromptsEndpoint

ApiEndpoint <|-- HealthEndpoint
ApiEndpoint <|-- MetricsEventCountsEndpoint
ApiEndpoint <|-- MetricsPrIntervalEndpoint
ApiEndpoint <|-- MetricsRepositoryActivityEndpoint
ApiEndpoint <|-- MetricsTrendingEndpoint
ApiEndpoint <|-- VisualizationTrendingChartEndpoint
ApiEndpoint <|-- VisualizationPrTimelineEndpoint
ApiEndpoint <|-- CollectEndpoint
ApiEndpoint <|-- WebhookEndpoint
ApiEndpoint <|-- McpCapabilitiesEndpoint
ApiEndpoint <|-- McpToolsEndpoint
ApiEndpoint <|-- McpResourcesEndpoint
ApiEndpoint <|-- McpPromptsEndpoint

class MetricsService {
  +get_event_counts(offset_minutes:int) dict
  +get_pr_interval(repo:str) dict
  +get_repository_activity(repo:str, hours:int) dict
  +get_trending(hours:int, limit:int) list
}

class VisualizationService {
  +trending_chart(hours:int, limit:int, format:str) bytes
  +pr_timeline(repo:str, format:str) bytes
}

class EventsRepository {
  +count_events_by_type(since_ts:int) dict
  +pr_timestamps(repo:str) list~datetime~
  +activity_by_repo(repo:str, since_ts:int) dict
  +trending_since(since_ts:int, limit:int) list
}

class EventsDao { <<abstract>> }
class WatchEventDao
class PullRequestEventDao
class IssuesEventDao
class EventsDaoFactory {
  +get_dao(type:str) EventsDao
}

class DBConnection {
  +execute(sql:str, params:dict) Cursor
  +fetchall() list
  +fetchone() any
}

class HealthReporter {
  +status() dict
}

HealthEndpoint ..> HealthReporter : uses
MetricsEventCountsEndpoint ..> MetricsService : uses
MetricsPrIntervalEndpoint ..> MetricsService : uses
MetricsRepositoryActivityEndpoint ..> MetricsService : uses
MetricsTrendingEndpoint ..> MetricsService : uses
VisualizationTrendingChartEndpoint ..> VisualizationService : uses
VisualizationPrTimelineEndpoint ..> VisualizationService : uses

MetricsService --> EventsRepository : queries
VisualizationService --> EventsRepository : reads data
EventsRepository --> EventsDaoFactory : gets DAOs
EventsDaoFactory --> EventsDao : provides
WatchEventDao --|> EventsDao
PullRequestEventDao --|> EventsDao
IssuesEventDao --|> EventsDao
EventsDao --> DBConnection : SQL (SELECT)
HealthReporter ..> DBConnection : optional ping

```

```mermaid
flowchart TB
  %% Interfaces
  subgraph Interfaces
    FastAPI["FastAPI Controllers\n(metrics, viz, health)"]
    MCP["MCP Tools\n(event_counts, pr_interval, trending_chart)"]
  end

  %% Read-side Services
  subgraph Services_Read
    MetricsService["MetricsService"]
    VisualizationService["VisualizationService"]
  end

  %% Protocols (DIP)
  subgraph Protocols
    EventsReadRepositoryProtocol["EventsReadRepositoryProtocol\n(Protocol)"]
    EventsWriteStoreProtocol["EventsWriteStoreProtocol\n(Protocol)"]
  end

  %% Repository + DAOs (Read)
  subgraph DataAccess_Read
    EventsRepository["EventsRepository"]
    EventsDaoFactory["EventsDaoFactory"]
    EventsDao["EventsDao (abstract)"]
    WatchEventDao["WatchEventDao"]
    PullRequestEventDao["PullRequestEventDao"]
    IssuesEventDao["IssuesEventDao"]
    DBConnection["DBConnection (aiosqlite)"]
  end

  %% Collector (Write)
  subgraph Ingestion_Write
    GitHubEventsCollector["GitHubEventsCollector"]
    ApiRequestReader["ApiRequestReader"]
    ApiResponseWriter["ApiResponseWriter"]
  end

  %% Storage / External
  SQLiteDB["SQLite Database\n(github_events.db)"]
  GitHubAPI["GitHub API /events"]

  %% Edges
  FastAPI --> MetricsService
  MCP --> MetricsService
  MetricsService --> EventsReadRepositoryProtocol
  VisualizationService --> EventsReadRepositoryProtocol
  EventsReadRepositoryProtocol -.-> EventsRepository
  EventsRepository --> EventsDaoFactory
  EventsDaoFactory --> EventsDao
  EventsDao <|-- WatchEventDao
  EventsDao <|-- PullRequestEventDao
  EventsDao <|-- IssuesEventDao
  WatchEventDao --> DBConnection
  PullRequestEventDao --> DBConnection
  IssuesEventDao --> DBConnection
  DBConnection --> SQLiteDB

  GitHubEventsCollector --> ApiRequestReader
  GitHubEventsCollector --> EventsWriteStoreProtocol
  EventsWriteStoreProtocol -.-> ApiResponseWriter
  ApiRequestReader --> GitHubAPI
  ApiResponseWriter --> SQLiteDB
```

```mermaid
flowchart TB
  %% Interfaces (HTTP + Tools)
  subgraph Interfaces
    MetricsEventCountsEndpoint["MetricsEventCountsEndpoint\nGET /metrics/event-counts"]
    MetricsPrIntervalEndpoint["MetricsPrIntervalEndpoint\nGET /metrics/pr-interval"]
    MetricsRepositoryActivityEndpoint["MetricsRepositoryActivityEndpoint\nGET /metrics/repository-activity"]
    MetricsTrendingEndpoint["MetricsTrendingEndpoint\nGET /metrics/trending"]
    VisualizationTrendingChartEndpoint["VisualizationTrendingChartEndpoint\nGET /visualization/trending-chart"]
    VisualizationPrTimelineEndpoint["VisualizationPrTimelineEndpoint\nGET /visualization/pr-timeline"]
    HealthEndpoint["HealthEndpoint\nGET /health"]
    McpTools["MCP Tools\n(event_counts, pr_interval, trending_chart, pr_timeline)"]
  end

  %% Services (Read side)
  subgraph Services_Read
    MetricsService["MetricsService"]
    VisualizationService["VisualizationService"]
    HealthReporter["HealthReporter"]
  end

  %% Protocols for DIP
  subgraph Protocols
    EventsReadRepositoryProtocol["EventsReadRepositoryProtocol\n(Protocol)"]
    EventsWriteStoreProtocol["EventsWriteStoreProtocol\n(Protocol)"]
  end

  %% Repository + DAOs (Read side)
  subgraph DataAccess_Read
    EventsRepository["EventsRepository"]
    EventsDaoFactory["EventsDaoFactory"]
    EventsDao["EventsDao (abstract)"]
    WatchEventDao["WatchEventDao"]
    PullRequestEventDao["PullRequestEventDao"]
    IssuesEventDao["IssuesEventDao"]
    DBConnection["DBConnection (aiosqlite)"]
  end

  %% Collector (Write side)
  subgraph Ingestion_Write
    GitHubEventsCollector["GitHubEventsCollector"]
    ApiRequestReader["ApiRequestReader"]
    ApiResponseWriter["ApiResponseWriter"]
  end

  %% Storage
  SQLiteDB["SQLite Database\n(github_events.db)"]

  %% External
  GitHubAPI["GitHub API /events"]

  %% Edges: Interfaces -> Services
  MetricsEventCountsEndpoint --> MetricsService
  MetricsPrIntervalEndpoint --> MetricsService
  MetricsRepositoryActivityEndpoint --> MetricsService
  MetricsTrendingEndpoint --> MetricsService
  VisualizationTrendingChartEndpoint --> VisualizationService
  VisualizationPrTimelineEndpoint --> VisualizationService
  HealthEndpoint --> HealthReporter
  McpTools --> MetricsService
  McpTools --> VisualizationService

  %% Edges: Services -> Protocols (read)
  MetricsService --> EventsReadRepositoryProtocol
  VisualizationService --> EventsReadRepositoryProtocol
  HealthReporter --> DBConnection

  %% Edges: Protocols -> Implementations (read)
  EventsReadRepositoryProtocol -.-> EventsRepository
  EventsRepository --> EventsDaoFactory
  EventsDaoFactory --> EventsDao
  EventsDao <|-- WatchEventDao
  EventsDao <|-- PullRequestEventDao
  EventsDao <|-- IssuesEventDao
  WatchEventDao --> DBConnection
  PullRequestEventDao --> DBConnection
  IssuesEventDao --> DBConnection
  DBConnection --> SQLiteDB

  %% Edges: Ingestion (write)
  GitHubEventsCollector --> ApiRequestReader
  GitHubEventsCollector --> EventsWriteStoreProtocol
  EventsWriteStoreProtocol -.-> ApiResponseWriter
  ApiRequestReader --> GitHubAPI
  ApiResponseWriter --> SQLiteDB
```

```mermaid
flowchart TB
  %% Interfaces (HTTP + Tools)
  subgraph Interfaces
    MetricsEventCountsEndpoint["MetricsEventCountsEndpoint\nGET /metrics/event-counts"]
    MetricsPrIntervalEndpoint["MetricsPrIntervalEndpoint\nGET /metrics/pr-interval"]
    MetricsRepositoryActivityEndpoint["MetricsRepositoryActivityEndpoint\nGET /metrics/repository-activity"]
    MetricsTrendingEndpoint["MetricsTrendingEndpoint\nGET /metrics/trending"]
    VisualizationTrendingChartEndpoint["VisualizationTrendingChartEndpoint\nGET /visualization/trending-chart"]
    VisualizationPrTimelineEndpoint["VisualizationPrTimelineEndpoint\nGET /visualization/pr-timeline"]
    HealthEndpoint["HealthEndpoint\nGET /health"]
    McpTools["MCP Tools\n(event_counts, pr_interval, trending_chart, pr_timeline)"]
  end

  %% Services (Read side)
  subgraph Services_Read
    MetricsService["MetricsService"]
    VisualizationService["VisualizationService"]
    HealthReporter["HealthReporter"]
  end

  %% Protocols for DIP
  subgraph Protocols
    EventsReadRepositoryProtocol["EventsReadRepositoryProtocol\n(Protocol)"]
    EventsWriteStoreProtocol["EventsWriteStoreProtocol\n(Protocol)"]
  end

  %% Repository + DAOs (Read side)
  subgraph DataAccess_Read
    EventsRepository["EventsRepository"]
    EventsDaoFactory["EventsDaoFactory"]
    EventsDao["EventsDao (abstract)"]
    WatchEventDao["WatchEventDao"]
    PullRequestEventDao["PullRequestEventDao"]
    IssuesEventDao["IssuesEventDao"]
    DBConnection["DBConnection (aiosqlite)"]
  end

  %% Collector (Write side)
  subgraph Ingestion_Write
    GitHubEventsCollector["GitHubEventsCollector"]
    ApiRequestReader["ApiRequestReader"]
    ApiResponseWriter["ApiResponseWriter"]
  end

  %% Storage
  SQLiteDB["SQLite Database\n(github_events.db)"]

  %% External
  GitHubAPI["GitHub API /events"]

  %% Edges: Interfaces -> Services
  MetricsEventCountsEndpoint --> MetricsService
  MetricsPrIntervalEndpoint --> MetricsService
  MetricsRepositoryActivityEndpoint --> MetricsService
  MetricsTrendingEndpoint --> MetricsService
  VisualizationTrendingChartEndpoint --> VisualizationService
  VisualizationPrTimelineEndpoint --> VisualizationService
  HealthEndpoint --> HealthReporter
  McpTools --> MetricsService
  McpTools --> VisualizationService

  %% Edges: Services -> Protocols (read)
  MetricsService --> EventsReadRepositoryProtocol
  VisualizationService --> EventsReadRepositoryProtocol
  HealthReporter --> DBConnection

  %% Edges: Protocols -> Implementations (read)
  EventsReadRepositoryProtocol -.-> EventsRepository
  EventsRepository --> EventsDaoFactory
  EventsDaoFactory --> EventsDao
  EventsDao <|-- WatchEventDao
  EventsDao <|-- PullRequestEventDao
  EventsDao <|-- IssuesEventDao
  WatchEventDao --> DBConnection
  PullRequestEventDao --> DBConnection
  IssuesEventDao --> DBConnection
  DBConnection --> SQLiteDB

  %% Edges: Ingestion (write)
  GitHubEventsCollector --> ApiRequestReader
  GitHubEventsCollector --> EventsWriteStoreProtocol
  EventsWriteStoreProtocol -.-> ApiResponseWriter
  ApiRequestReader --> GitHubAPI
  ApiResponseWriter --> SQLiteDB
```

### 🌐 API Endpoints

#### Core Metrics
- **Health**: `GET /health`
- **Event Counts**: `GET /metrics/event-counts?offset_minutes=60`
- **PR Intervals**: `GET /metrics/pr-interval?repo=owner/repo`
- **Repository Activity**: `GET /metrics/repository-activity?repo=owner/repo&hours=24`
- **Trending Repos**: `GET /metrics/trending?hours=24&limit=10`

#### Enhanced Monitoring
- **Repository Health**: `GET /metrics/repository-health?repo=owner/repo&hours=168`
- **Developer Productivity**: `GET /metrics/developer-productivity?repo=owner/repo&hours=168`
- **Security Monitoring**: `GET /metrics/security-monitoring?repo=owner/repo&hours=168`
- **Event Anomalies**: `GET /metrics/event-anomalies?repo=owner/repo&hours=168`
- **Release/Deployment**: `GET /metrics/release-deployment?repo=owner/repo&hours=720`
- **Community Engagement**: `GET /metrics/community-engagement?repo=owner/repo&hours=168`
- **Event Types Summary**: `GET /metrics/event-types-summary?repo=owner/repo&hours=168`

#### Commit Monitoring & Change Tracking
- **Recent Commits**: `GET /commits/recent?repo=owner/repo&hours=24&limit=50`
- **Change Summary**: `GET /commits/summary?repo=owner/repo&hours=168`
- **Commit Details**: `GET /commits/{sha}?repo=owner/repo`
- **Commit Files**: `GET /commits/{sha}/files?repo=owner/repo`
- **Multi-Repo Monitoring**: `GET /monitoring/commits?repos=repo1,repo2&hours=24`
- **Commits by Category**: `GET /monitoring/commits/categories?repo=owner/repo`
- **Commits by Author**: `GET /monitoring/commits/authors?repo=owner/repo&hours=168`
- **High-Impact Commits**: `GET /monitoring/commits/impact?repo=owner/repo&min_impact_score=70`

#### Visualization & Docs
- **Trending Chart**: `GET /visualization/trending-chart?hours=24&limit=5&format=png`
- **Interactive API Docs**: `http://localhost:8000/docs`

### 📈 Live Dashboard URLs
- **Local Dashboard**: `file://path/to/docs/index.html`
- **GitHub Pages**: [https://sparesparrow.github.io/github-events](https://sparesparrow.github.io/github-events)
- **API Server**: `http://localhost:8000`

## Setup (Monitor and Dashboard)

1) Python env
- python -m venv venv
- source venv/bin/activate
- pip install -r requirements.txt

2) Initialize Database
- sqlite3 database/events.db < database/schema.sql

3) Run Event Monitor
- python scripts/github_monitor.py            # continuous
- python scripts/github_monitor.py --once     # single cycle (useful in CI)
Optional: export GITHUB_TOKEN for higher limits.

4) Export Dashboard Data
- python scripts/data_exporter.py

5) MCP Server
- python scripts/mcp_server.py

## Docker Deployment

The project includes Docker support for containerized deployment:

- **Dockerfile**: Multi-stage build for production deployment
- **docker-compose.yml**: Local development and testing setup
- **entrypoint.sh**: Container initialization script
- **deploy.sh**: Deployment automation script

Quick start with Docker:
```bash
cd ./
docker-compose up -d
```

See `docs/DEPLOYMENT.md` for detailed Docker deployment instructions.

## ☁️ AWS DynamoDB Backend

For scalable production deployment, the system supports AWS DynamoDB:

```bash
# Configure DynamoDB backend
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-east-1
export DYNAMODB_TABLE_PREFIX=github-events-

# Create DynamoDB tables
python scripts/setup_dynamodb.py create

# Start with DynamoDB backend
python -m src.github_events_monitor.api
```

See [docs/DYNAMODB_SETUP.md](docs/DYNAMODB_SETUP.md) for detailed configuration.

### MCP Postgres (read-only) integration

Connect a read-only PostgreSQL database via the MCP Postgres server to inspect schemas and run queries through your MCP client.

Run the server:
- Docker: `docker run -i --rm mcp/postgres postgresql://host.docker.internal:5432/mydb`
- NPX: `npx -y @modelcontextprotocol/server-postgres postgresql://localhost/mydb`

Client configuration:
- Edit `.cursor/mcp.json` and set `POSTGRES_URL_READONLY` environment variable (e.g., `postgresql://readonly:pass@localhost:5432/mydb`).
- The repo includes a pre-wired `postgres` MCP server entry that uses `${POSTGRES_URL_READONLY}`.

Security:
- Use a read-only database role/account.
- Do not store credentials in the repo; use environment variables or secret managers.

## GitHub Pages
- Push to main branch.
- Enable Pages from Settings → Pages → Deploy from a branch → main → /docs.

## Documentation

Comprehensive documentation is available in the `docs/` directory. See **[docs/README.md](docs/README.md)** for the complete documentation index.

### **Quick Reference**
- **[CHANGELOG.md](CHANGELOG.md)** - Complete version history and feature timeline
- **[docs/API.md](docs/API.md)** - REST API reference with 25+ endpoints
- **[docs/ENHANCED_MONITORING.md](docs/ENHANCED_MONITORING.md)** - 6 comprehensive monitoring use cases
- **[docs/DATABASE_ABSTRACTION.md](docs/DATABASE_ABSTRACTION.md)** - SOLID architecture with SQLite/DynamoDB
- **[docs/AGENT_ECOSYSTEM.md](docs/AGENT_ECOSYSTEM.md)** - Claude Agent SDK integration
- **[docs/DOCKER_USAGE.md](docs/DOCKER_USAGE.md)** - Comprehensive Docker deployment guide

### **Specialized Guides**
- **[docs/COMMIT_MONITORING.md](docs/COMMIT_MONITORING.md)** - Detailed commit tracking and analysis
- **[docs/DYNAMODB_SETUP.md](docs/DYNAMODB_SETUP.md)** - AWS DynamoDB configuration
- **[docs/OPENSSL_REFACTORING_MONITOR.md](docs/OPENSSL_REFACTORING_MONITOR.md)** - DevOps process monitoring

## Assumptions

- GitHub API public events endpoint `/events` is used for general monitoring; optional per-repo events endpoints are used when `TARGET_REPOSITORIES` is set.
- SQLite is sufficient for this assignment; for production, a managed SQL database and a retention policy are recommended.
- Metrics are computed from stored events; freshness depends on poll cadence or manual collection.
- Authentication to this REST API is not required for the assignment scope. Provide a `GITHUB_TOKEN` to increase GitHub rate limits.

## C4 Model (Level 1)

System Context describing key containers and interactions:

```mermaid
graph TD
    A["Person: API Consumer"] -->|HTTP| B["Container: FastAPI REST API"]
    A2["Person: Dashboard User"] -->|HTTPS| D["Container: GitHub Pages (docs/)"]
    B -->|SQL| C["Container: Events DB (SQLite)"]
    E["Container: Event Monitor Service"] -->|writes| C
    E -->|GET /events| F["External System: GitHub API"]
    G["Container: Data Exporter"] -->|reads| C
    G -->|publishes| D
```

## AWS Static Hosting (S3 + optional CloudFront)

You can deploy the generated dashboard to Amazon S3 using the workflow `.github/workflows/aws_deploy.yml`.

Prerequisites:
- Create an S3 bucket for static website hosting (enable public read for objects or serve via CloudFront OAI).
- Create an IAM user with least-privilege permissions for `s3:PutObject`, `s3:ListBucket`, `s3:DeleteObject`, and optional CloudFront invalidation.
- Store credentials as GitHub Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.

Run the workflow:
- Actions → "Deploy static dashboard to AWS S3" → Run workflow
  - `s3_bucket`: your-bucket-name
  - `aws_region`: e.g., `us-east-1`
  - `cloudfront_distribution_id` (optional): your distribution ID for cache invalidation

Notes:
- The workflow builds the JSON artifacts into `pages_content/` and syncs to S3.
- If CloudFront is configured, the workflow will invalidate `/*` to serve latest content.
- Static site index can be `pages_content/index.html` or sync bucket root depending on your S3 website configuration.

## Notes
- created_at_ts (epoch) enables correct time filtering and SQLite date ops.
- For production, consider PostgreSQL, containerization, and a retention policy for events.

## Release Notes

### 1.1.0
- Added PR timeline visualization endpoint: `GET /visualization/pr-timeline`.
- Added optional webhook receiver: `POST /webhook` for monitored event types.
- Dashboard exporter now writes `trending.json`, `event_counts_10.json`, `event_counts_60.json`, `data_status.json`, and `config.json`.
- Background poller now respects GitHub `X-Poll-Interval` when available.
- GitHub Pages workflow for scheduled/manual dashboard publishing.

## Project Structure

```
github-events-clone/
├── src/                    # Source code
├── tests/                  # Test suite
├── docs/                   # Documentation
├── (docker files at repo root)                 # Docker configurations
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   └── deploy.sh
├── .github/workflows/      # CI/CD workflows
├── scripts/                # Utility scripts
├── scripts/                # Service layer
├── scripts/                    # MCP server
└── database/               # Database schema
```

## Class Diagram (Key Classes)

```mermaid
classDiagram
  direction TB

  class GitHubEventsCollector {
    +__init__(reader: ApiRequestReader, writer: ApiResponseWriter)
    +fetch_events(limit) List~GitHubEvent~
    +fetch_repository_events(repo, limit) List~GitHubEvent~
    +store_events(events) int
    +get_event_counts_by_type(offset_minutes) dict
    +get_avg_pr_interval(repo) dict
    +get_repository_activity_summary(repo, hours) dict
    +get_trending_repositories(hours, limit) List~dict~
    +get_event_counts_timeseries(hours, bucket_minutes) List~dict~
    +get_pr_timeline(repo, days) List~dict~
    +start_monitor(repo, monitored_events, interval_seconds) int
    +stop_monitor(id) bool
  }

  class ApiRequestReader {
    +__init__(github_token, user_agent, http_client)
    +fetch_global_events(since_etag) List~GitHubEvent~
    +fetch_repo_events(repo, since_etag) List~GitHubEvent~
    +get_rate_limit() dict
    +is_throttled() bool
  }

  class ApiResponseWriter {
    +__init__(db_path, db_manager)
    +store_events(events: List~GitHubEvent~) int
    +upsert_etag(key: str, etag: str)
    +get_etag(key: str) str
    +query_events(filter) List~GitHubEvent~
    +count_by_type(since) dict
    +avg_pr_interval(repo) dict
  }

  class GitHubEvent {
    +id: str
    +event_type: str
    +created_at: datetime
    +repo_name: str
    +actor_login: str
    +payload: dict
  }

  %% Routing and dispatch layer
  class EndpointType {
    EVENT_COUNTS
    AVG_PR_INTERVAL
    REPO_ACTIVITY_SUMMARY
    TRENDING_REPOS
    EVENTS_TIMESERIES
    PR_TIMELINE
    START_MONITOR
    STOP_MONITOR
    ACTIVE_MONITORS
    MONITOR_EVENTS
    MONITOR_EVENTS_GROUPED
  }

  class EndpointDispatcher {
    +endpoints: dict~EndpointType, ApiEndpoint~
    +__init__(collector: GitHubEventsCollector)
    +register_endpoint(endpoint_type: EndpointType, endpoint: ApiEndpoint)
    +dispatch(endpoint_type: EndpointType, request: Request) Response
    +get_route_map() dict~str, EndpointType~
  }

  class ApiEndpoint {
    +route: str
    +method: str
    +endpoint_type: EndpointType
    +params_schema: dict
    +response_schema: dict
    +__init__(collector: GitHubEventsCollector, endpoint_type: EndpointType)
    +handle(request: Request) Response
    +validate_params(params) dict
  }

  class EventCountsEndpoint {
    +endpoint_type = EndpointType.EVENT_COUNTS
    +route="/metrics/event-counts"
    +method="GET"
    +handle(request: Request) Response
  }

  class AvgPrIntervalEndpoint {
    +endpoint_type = EndpointType.AVG_PR_INTERVAL
    +route="/metrics/avg-pr-interval"
    +method="GET"
    +handle(request: Request) Response
  }

  class RepoActivitySummaryEndpoint {
    +endpoint_type = EndpointType.REPO_ACTIVITY_SUMMARY
    +route="/metrics/repo-activity"
    +method="GET"
    +handle(request: Request) Response
  }

  class TrendingReposEndpoint {
    +endpoint_type = EndpointType.TRENDING_REPOS
    +route="/metrics/trending"
    +method="GET"
    +handle(request: Request) Response
  }

  class EventsTimeseriesEndpoint {
    +endpoint_type = EndpointType.EVENTS_TIMESERIES
    +route="/metrics/events-timeseries"
    +method="GET"
    +handle(request: Request) Response
  }

  class PrTimelineEndpoint {
    +endpoint_type = EndpointType.PR_TIMELINE
    +route="/metrics/pr-timeline"
    +method="GET"
    +handle(request: Request) Response
  }

  class StartMonitorEndpoint {
    +endpoint_type = EndpointType.START_MONITOR
    +route="/monitors/start"
    +method="POST"
    +handle(request: Request) Response
  }

  class StopMonitorEndpoint {
    +endpoint_type = EndpointType.STOP_MONITOR
    +route="/monitors/123/stop"
    +method="POST"
    +handle(request: Request) Response
  }

  class ActiveMonitorsEndpoint {
    +endpoint_type = EndpointType.ACTIVE_MONITORS
    +route="/monitors"
    +method="GET"
    +handle(request: Request) Response
  }

  class MonitorEventsEndpoint {
    +endpoint_type = EndpointType.MONITOR_EVENTS
    +route="/monitors/123/events"
    +method="GET"
    +handle(request: Request) Response
  }

  class MonitorEventsGroupedEndpoint {
    +endpoint_type = EndpointType.MONITOR_EVENTS_GROUPED
    +route="/monitors/123/events/grouped"
    +method="GET"
    +handle(request: Request) Response
  }

  class Request {
    +query: dict
    +body: dict
    +path_params: dict
    +headers: dict
  }

  class Response {
    +status: int
    +body: dict
    +headers: dict
  }

  %% Relationships
  GitHubEventsCollector *-- ApiRequestReader : owns
  GitHubEventsCollector *-- ApiResponseWriter : owns
  GitHubEventsCollector ..> GitHubEvent : orchestrates
  ApiRequestReader ..> GitHubEvent : normalizes
  ApiResponseWriter ..> GitHubEvent : persists

  %% Dispatch relationships
  EndpointDispatcher *-- ApiEndpoint : owns
  EndpointDispatcher ..> EndpointType : switches on
  EndpointDispatcher ..> GitHubEventsCollector : delegates to
  
  %% Inheritance
  ApiEndpoint <|-- EventCountsEndpoint
  ApiEndpoint <|-- AvgPrIntervalEndpoint
  ApiEndpoint <|-- RepoActivitySummaryEndpoint
  ApiEndpoint <|-- TrendingReposEndpoint
  ApiEndpoint <|-- EventsTimeseriesEndpoint
  ApiEndpoint <|-- PrTimelineEndpoint
  ApiEndpoint <|-- StartMonitorEndpoint
  ApiEndpoint <|-- StopMonitorEndpoint
  ApiEndpoint <|-- ActiveMonitorsEndpoint
  ApiEndpoint <|-- MonitorEventsEndpoint
  ApiEndpoint <|-- MonitorEventsGroupedEndpoint

  %% Endpoint type associations
  EventCountsEndpoint --> EndpointType : EVENT_COUNTS
  AvgPrIntervalEndpoint --> EndpointType : AVG_PR_INTERVAL
  RepoActivitySummaryEndpoint --> EndpointType : REPO_ACTIVITY_SUMMARY
  TrendingReposEndpoint --> EndpointType : TRENDING_REPOS
  EventsTimeseriesEndpoint --> EndpointType : EVENTS_TIMESERIES
  PrTimelineEndpoint --> EndpointType : PR_TIMELINE
  StartMonitorEndpoint --> EndpointType : START_MONITOR
  StopMonitorEndpoint --> EndpointType : STOP_MONITOR
  ActiveMonitorsEndpoint --> EndpointType : ACTIVE_MONITORS
  MonitorEventsEndpoint --> EndpointType : MONITOR_EVENTS
  MonitorEventsGroupedEndpoint --> EndpointType : MONITOR_EVENTS_GROUPED

  ApiEndpoint --> Request : handles
  ApiEndpoint --> Response : returns


```

## Updated Imports

Use `event_collector`:
```python
from src.github_events_monitor.event_collector import GitHubEventsCollector
```
