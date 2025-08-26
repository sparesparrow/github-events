# GitHub Events Monitor

A Python-based service that monitors GitHub Events (WatchEvent, PullRequestEvent, IssuesEvent), stores them in SQLite, exposes data through an MCP server (each tool = API endpoint), and publishes interactive visualizations to a GitHub Pages site from the docs/ folder.

## Architecture (C4 L1)

[Person: Dashboard User] → [Container: GitHub Pages (docs/)] ← [Container: Data Exporter] ← [Container: Events DB (SQLite)] ← [Container: Event Monitor Service] ← [External System: GitHub API /events]
[Person: API Consumer] → [Container: MCP Server] → [Container: Events DB (SQLite)]

## Components

- Event Monitor: Polls https://api.github.com/events, filters target types, stores to SQLite, computes PR metrics.
- MCP Server: Tools to retrieve metrics/data directly from the DB.
- Data Exporter: Builds docs/data.json and Plotly HTML charts in docs/.
- GitHub Pages: Static dashboard served from docs/.

## Setup

1) Python env
- python -m venv venv
- source venv/bin/activate
- pip install -r requirements.txt

2) Initialize DB
- sqlite3 database/events.db < database/schema.sql

3) Run monitor
- python service/github_monitor.py            # continuous
- python service/github_monitor.py --once     # single cycle (useful in CI)
Optional: export GITHUB_TOKEN for higher limits.

4) Export dashboard data
- python service/data_exporter.py

5) MCP server
- python mcp/server.py

## GitHub Pages
- Push to main branch.
- Enable Pages from Settings → Pages → Deploy from a branch → main → /docs.

## Notes
- created_at_ts (epoch) enables correct time filtering and SQLite date ops.
- For production, consider PostgreSQL, containerization, and a retention policy for events.
