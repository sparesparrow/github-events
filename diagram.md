# C4 Model - Level 1: System Context Diagram

This diagram provides a high-level overview of the GitHub Events Monitor system, following the C4 model (https://c4model.com/). It shows the system in context with users and external dependencies.

## Mermaid Diagram

```mermaid
C4Context
    title System Context Diagram for GitHub Events Monitor

    Person(user, "User/Developer", "Queries metrics and visualizations via REST API or MCP")

    System(api, "GitHub Events Monitor", "Python application that collects events, computes metrics, and serves API/visualizations")

    SystemDb(db, "SQLite Database", "Stores collected GitHub events (WatchEvent, PullRequestEvent, IssuesEvent) with timestamps")

    System_Ext(github, "GitHub API", "External service providing public events stream")

    Rel(user, api, "Queries metrics/visualizations", "HTTP (REST) or MCP")
    Rel(api, db, "Reads/Writes events and metrics")
    Rel(api, github, "Polls events periodically", "HTTPS (API calls)")

    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

### Explanation
- **User/Developer**: Interacts with the system to get insights on GitHub activity.
- **GitHub Events Monitor**: Core application handling event collection, storage, and API serving.
- **SQLite Database**: Persistent storage for events.
- **GitHub API**: Source of raw event data.

This is a Level 1 (System Context) diagram, focusing on the system as a black box and its interactions.
