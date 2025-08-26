# GitHub Events Monitor

A Python-based service that monitors GitHub Events (WatchEvent, PullRequestEvent, IssuesEvent), stores them in SQLite, exposes data through an MCP server (each tool = API endpoint), and publishes interactive visualizations to a GitHub Pages site from the docs/ folder.

## Architecture (C4 L1)

[Person: Dashboard User] → [Container: GitHub Pages (docs/)] ← [Container: Data Exporter] ← [Container: Events DB (SQLite)] ← [Container: Event Monitor Service] ← [External System: GitHub API /events]
[Person: API Consumer] → [Container: MCP Server] → [Container: Events DB (SQLite)]

## Components

- Event Monitor: Polls GitHub API events, filters target types, stores to SQLite, computes PR metrics.
  - Can monitor specific repositories via `TARGET_REPOSITORIES` environment variable
  - Falls back to public events if no target repositories specified
- MCP Server: Tools to retrieve metrics/data directly from the DB.
- Data Exporter: Builds docs/data.json and Plotly HTML charts in docs/.
- GitHub Pages: Static dashboard served from docs/.

## Configuration

The service can be configured via environment variables:

- `TARGET_REPOSITORIES`: Comma-separated list of repositories to monitor (e.g., "owner/repo1,owner/repo2")
- `GITHUB_TOKEN`: GitHub personal access token for higher API rate limits
- `DATABASE_PATH`: Path to SQLite database file
- `POLL_INTERVAL`: Polling interval in seconds (default: 300)

## Setup

1) Python env
- python -m venv venv
- source venv/bin/activate
- pip install -r requirements.txt

2) Initialize Database
- sqlite3 database/events.db < database/schema.sql

3) Run Event Monitor
- python service/github_monitor.py            # continuous
- python service/github_monitor.py --once     # single cycle (useful in CI)
Optional: export GITHUB_TOKEN for higher limits.

4) Export Dashboard Data
- python service/data_exporter.py

5) MCP Server
- python mcp/server.py

## Docker Deployment

The project includes Docker support for containerized deployment:

- **Dockerfile**: Multi-stage build for production deployment
- **docker-compose.yml**: Local development and testing setup
- **entrypoint.sh**: Container initialization script
- **deploy.sh**: Deployment automation script

Quick start with Docker:
```bash
cd docker/
docker-compose up -d
```

See `docs/DEPLOYMENT.md` for detailed Docker deployment instructions.

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

Comprehensive documentation is available in the `docs/` directory:

- **API.md**: REST API reference and endpoints
- **ARCHITECTURE.md**: System architecture and design decisions
- **ASSIGNMENT.md**: Project requirements and specifications
- **DEPLOYMENT.md**: Deployment guides and configurations
- **WORKFLOWS.md**: CI/CD workflow documentation
- **diagram.md**: System architecture diagrams

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

## Project Structure

```
github-events-clone/
├── src/                    # Source code
├── tests/                  # Test suite
├── docs/                   # Documentation
├── docker/                 # Docker configurations
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   └── deploy.sh
├── .github/workflows/      # CI/CD workflows
├── scripts/                # Utility scripts
├── service/                # Service layer
├── mcp/                    # MCP server
└── database/               # Database schema
```
