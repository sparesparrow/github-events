# GitHub Events Monitor

A consolidated Python project that provides a FastAPI REST API and an MCP (Model Context Protocol) server for monitoring GitHub Events. This repository merges prior implementations into a single, clean `src/`-based layout with minimized duplication.

## Features

- FastAPI REST API serving metrics and visualizations
- MCP server exposing tools, resources, and prompts
- SQLite storage with indices; optional future Postgres migration
- Tested collector logic, endpoints, and end-to-end flows

## Project Structure

```
.
├── README.md
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── src/
│   └── github_events_monitor/
│       ├── __init__.py
│       ├── __main__.py
│       ├── api.py
│       ├── collector.py
│       ├── config.py
│       └── mcp_server.py
└── tests/
    ├── integration/
    │   └── test_integration.py
    └── unit/
        ├── test_api.py
        └── test_collector.py
```

## Quick Start

- Install: `pip install -r requirements.txt`
- Run API: `python -m github_events_monitor.api`
- Run MCP: `python -m github_events_monitor.mcp_server`
- Env vars: `DATABASE_PATH`, `GITHUB_TOKEN`, `POLL_INTERVAL`

## Docker

- Build: `docker build -t github-events-monitor .`
- Run: `docker compose up -d` (set `HOST_PORT` and `API_PORT` to avoid conflicts)
- Port mapping examples:
  - Default: host 8000 -> container 8000
  - Custom: `HOST_PORT=18000 API_PORT=8080 docker compose up -d`
  - Raw docker: `docker run -p 18000:8080 -e API_PORT=8080 github-events-monitor`

## Testing

- Run all: `pytest`
- Unit only: `pytest tests/unit`
- Integration: `pytest tests/integration`

## Use Cases

### Real-time repository health check
Monitor the short-term activity and overall health of a repository when you need a quick pulse (on-call, triage, stakeholder reviews). Query event volume by type over the last N minutes/hours and see whether things are quiet or spiking. Use via REST (`GET /metrics/event-counts?offset_minutes=60`, `GET /metrics/repository-activity?repo=owner/repo&hours=24`) or MCP tools (`get_event_counts`, `get_repository_activity`) to embed this pulse check in an AI agent or dashboard.

### Release readiness pulse
Assess if a codebase is trending toward a stable release by looking at PR cadence and recent activity distribution. The average interval between PR openings, plus the distribution of Issues/PR events, gives a lightweight view of pace and churn. Use REST (`GET /metrics/pr-interval?repo=owner/repo`) or MCP (`get_avg_pr_interval`) and combine with `get_repository_activity` for a simple go/no-go signal.

### Contributor velocity tracking
Track how frequently contributors open pull requests as a proxy for development velocity. Useful for sprint retros, productivity checks, and spotting bottlenecks. Use `GET /metrics/pr-interval?repo=owner/repo` or MCP `get_avg_pr_interval` and compare over time windows (e.g., daily/weekly) to see acceleration or slowdown.

### Incident and anomaly detection
Detect sudden spikes in Issues or PRs that may indicate incidents, regressions, or flaky behavior. Poll `GET /metrics/event-counts?offset_minutes=10` (or MCP `get_event_counts`) and alert when counts cross thresholds. Pair with the trending endpoint to see which repositories are driving the spike.

### Community interest signal (watch events)
Use WatchEvent counts as a quick interest/awareness signal for marketing or devrel. Compare watch vs PR/Issues balance to separate hype from contribution. Fetch via REST (`GET /metrics/event-counts`, `GET /metrics/trending`) or MCP (`get_event_counts`, `get_trending_repositories`).

### Competitive repo watchlist
Monitor competitor or peer projects for activity surges and engagement patterns. Schedule periodic calls to `get_trending_repositories` (REST: `GET /metrics/trending?hours=24&limit=20`) and log results for longitudinal tracking; use MCP in an agent that summarizes notable changes.

### Weekly trends and digest generation
Produce a weekly digest highlighting most active repositories, PR cadence changes, and activity breakdowns. Drive it with `get_trending_repositories` and `get_repository_activity` and render visuals via `GET /visualization/trending-chart?hours=168&limit=10&format=png`. An AI agent can use the MCP prompts (`analyze_repository_trends`, `create_monitoring_dashboard_config`) to generate narrative summaries.

### Analyst notebook exploration
For data analysts, mount the database volume and query SQLite directly for custom slices. Run via Docker with `-v ./data:/app/data`, then analyze `/app/data/github_events.db` using your notebook: SELECT by `repo_name`, `event_type`, and time windows; build your own time-series. Use the REST/MCP endpoints for quick checks and the DB for custom analysis.

### Agent-powered operations dashboard
Use MCP Inspector (`mcp dev src/github_events_monitor/mcp_server.py:main -e .`) or integrate with an MCP-capable IDE/agent to expose tools like `get_event_counts`, `get_repository_activity`, and `get_trending_repositories`. Provide operators with chat-driven commands and ready-made prompts to assess repository health and decide next actions without writing queries.

## Notes on the Merge

- Kept the `gh_events-2` SQLite collector and API/MCP implementations as primary (well-tested, includes full test suite).
- Dropped `gh_events-1` Postgres-specific server; if needed later, port `init.sql` and asyncpg logic behind a storage interface.
- Consolidated packaging (pyproject), scripts, and configs into root. Removed scattered duplicates.

## Known Issues / Follow-ups

- Visualization endpoints are basic; consider a small frontend or richer charts.
- MCP recent-events resource is a placeholder; add a collector method to fetch latest by type.
- Security: never bake secrets. Use env vars for `GITHUB_TOKEN`.
- Consider a storage abstraction to switch between SQLite and Postgres seamlessly.

## License

MIT

## Assignment Mapping
This project implements the specified assignment requirements as follows:

- **Event Collection**: Streams WatchEvent, PullRequestEvent, and IssuesEvent from https://api.github.com/events. Implemented in `src/github_events_monitor/collector.py` with polling and SQLite storage.
- **Metric: Average time between pull requests for a given repository**: Served via REST endpoint `GET /metrics/pr-interval?repo=owner/repo`. Calculates based on stored PullRequestEvent timestamps.
- **Metric: Total number of events grouped by type for a given offset**: Served via REST endpoint `GET /metrics/event-counts?offset_minutes=X`. Counts events created in the last X minutes, grouped by type.
- **Bonus: Visualization Endpoint**: Provides charts for metrics, e.g., `GET /visualization/trending-chart?hours=168&limit=10&format=png`.
- **README and Diagram**: See below for how to run and assumptions. A C4 Level 1 diagram is in [diagram.md](diagram.md).

## How to Run
1. Clone the repo: `git clone https://github.com/sparesparrow/github-events.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your values (especially GITHUB_TOKEN).
4. Run the API: `python -m github_events_monitor.api`
5. (Optional) Run MCP server: `python -m github_events_monitor.mcp_server`
6. Access API at http://localhost:8000 (or configured port). Docs at /docs.

## Assumptions
- GitHub API rate limits are respected via POLL_INTERVAL (default 60s).
- Public events only; no authentication required beyond token for higher limits.
- SQLite for simplicity; assumes low-to-medium event volume.
- Timezone handling: Uses UTC for all timestamps.
- Offset in minutes for event counts; assumes server time for "now".
- Visualization is basic (PNG/SVG); extendable for more formats.

For architecture overview, see [diagram.md](diagram.md) with C4 Level 1 diagram.
