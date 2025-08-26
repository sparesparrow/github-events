from fastmcp import FastMCP
import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, List

DB_PATH = "database/events.db"
mcp = FastMCP("github-events-mcp")

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

@mcp.tool
def get_average_pr_time(repo_name: str) -> Dict:
    """
    Return average time between PullRequestEvent occurrences (minutes/hours) for a given repository.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT avg_time_between_prs_minutes, total_prs, last_updated FROM pr_metrics WHERE repo_name = ?",
            (repo_name,),
        )
        row = cur.fetchone()
    if not row:
        return {"repository": repo_name, "error": "No PR data found", "last_updated": now_iso()}
    avg_m, total_prs, lu = row
    return {
        "repository": repo_name,
        "average_time_between_prs_minutes": round(avg_m, 2),
        "average_time_between_prs_hours": round(avg_m / 60.0, 2),
        "total_pull_requests": int(total_prs),
        "last_updated": lu,
    }

@mcp.tool
def get_events_by_offset(offset_minutes: int) -> Dict:
    """
    Return counts of events grouped by type for events created within the last N minutes.
    """
    if offset_minutes < 0:
        offset_minutes = 0
    cutoff_ts = int(datetime.now(timezone.utc).timestamp()) - (offset_minutes * 60)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT type, COUNT(*) FROM events
            WHERE created_at_ts >= ?
            GROUP BY type
            """,
            (cutoff_ts,),
        )
        data = dict(cur.fetchall())
    return {
        "offset_minutes": offset_minutes,
        "event_counts": {k: int(v) for k, v in data.items()},
        "total_events": int(sum(data.values())),
        "time_range_end": now_iso(),
    }

@mcp.tool
def get_repository_activity(repo_name: str, limit: int = 50) -> Dict:
    """
    Return recent events for a repository.
    """
    limit = max(1, min(limit, 200))
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, type, actor_login, created_at, payload
            FROM events
            WHERE repo_name = ?
            ORDER BY created_at_ts DESC
            LIMIT ?
            """,
            (repo_name, limit),
        )
        rows = cur.fetchall()
    events: List[Dict] = []
    for eid, etype, actor, cat, payload in rows:
        events.append({
            "id": eid,
            "type": etype,
            "actor": actor,
            "created_at": cat,
            "payload": json.loads(payload) if payload else {},
        })
    return {"repository": repo_name, "count": len(events), "events": events}

@mcp.tool
def get_top_repositories(limit: int = 10) -> Dict:
    """
    Return repositories with most tracked activity and breakdown by type.
    """
    limit = max(1, min(limit, 50))
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT repo_name,
                   COUNT(*) AS total_events,
                   SUM(CASE WHEN type='WatchEvent' THEN 1 ELSE 0 END) AS watches,
                   SUM(CASE WHEN type='PullRequestEvent' THEN 1 ELSE 0 END) AS pull_requests,
                   SUM(CASE WHEN type='IssuesEvent' THEN 1 ELSE 0 END) AS issues
            FROM events
            WHERE repo_name IS NOT NULL
            GROUP BY repo_name
            ORDER BY total_events DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
    repos = []
    for name, total, w, pr, is_ in rows:
        repos.append({
            "name": name,
            "total_events": int(total),
            "watches": int(w or 0),
            "pull_requests": int(pr or 0),
            "issues": int(is_ or 0),
        })
    return {"count": len(repos), "top_repositories": repos}

@mcp.tool
def get_event_statistics() -> Dict:
    """
    Return overall statistics about the stored events.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT type, COUNT(*) FROM events GROUP BY type ORDER BY COUNT(*) DESC")
        event_types = {k: int(v) for k, v in cur.fetchall()}

        cur.execute("SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM events")
        earliest, latest, total = cur.fetchone() or (None, None, 0)

        cur.execute("SELECT COUNT(DISTINCT repo_name) FROM events")
        unique_repos = int(cur.fetchone()[0] or 0)

        cur.execute("SELECT COUNT(DISTINCT actor_login) FROM events")
        unique_actors = int(cur.fetchone()[0] or 0)

    return {
        "total_events": int(total or 0),
        "event_types": event_types,
        "date_range": {"earliest": earliest, "latest": latest},
        "unique_repositories": unique_repos,
        "unique_actors": unique_actors,
        "last_updated": now_iso(),
    }

if __name__ == "__main__":
    mcp.run()
