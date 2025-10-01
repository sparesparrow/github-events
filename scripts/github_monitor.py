import os
import sqlite3
import requests
import json
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("github-monitor")

API_URL = "https://api.github.com/events"
DB_PATH = os.environ.get("DB_PATH", "database/events.db")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # optional, boosts rate limits

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def iso_to_epoch_s(iso_str: str) -> int:
    # GitHub timestamps are like "2025-08-26T00:14:00Z"
    dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
    return int(dt.replace(tzinfo=timezone.utc).timestamp())

def ensure_schema():
    with sqlite3.connect(DB_PATH) as conn, open("database/schema.sql", "r") as f:
        conn.executescript(f.read())

def fetch_events(etag: Optional[str]) -> Tuple[List[Dict], Optional[str], Optional[int]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    if etag:
        headers["If-None-Match"] = etag

    r = requests.get(API_URL, headers=headers, timeout=30)
    poll_interval = None
    try:
        poll_interval = int(r.headers.get("X-Poll-Interval", "60"))
    except Exception:
        poll_interval = 60

    if r.status_code == 304:
        log.info("No new events (304). Suggested poll interval: %ss", poll_interval)
        return [], etag, poll_interval
    r.raise_for_status()
    new_etag = r.headers.get("ETag")

    events = r.json()
    # Filter to required event types - expanded for comprehensive monitoring
    wanted = {
        # Core development events
        'WatchEvent',           # Stars/watching repositories
        'PullRequestEvent',     # Pull requests opened/closed/merged
        'IssuesEvent',          # Issues opened/closed/labeled
        'PushEvent',           # Code pushes to repositories
        'ForkEvent',           # Repository forks
        'CreateEvent',         # Branch/tag creation
        'DeleteEvent',         # Branch/tag deletion
        'ReleaseEvent',        # Releases published
        
        # Collaboration events
        'CommitCommentEvent',  # Comments on commits
        'IssueCommentEvent',   # Comments on issues
        'PullRequestReviewEvent',      # PR reviews
        'PullRequestReviewCommentEvent', # Comments on PR reviews
        
        # Repository management events
        'PublicEvent',         # Repository made public
        'MemberEvent',         # Collaborators added/removed
        'TeamAddEvent',        # Teams added to repositories
        
        # Security and maintenance events
        'GollumEvent',         # Wiki pages created/updated
        'DeploymentEvent',     # Deployments created
        'DeploymentStatusEvent', # Deployment status updates
        'StatusEvent',         # Commit status updates
        'CheckRunEvent',       # Check runs completed
        'CheckSuiteEvent',     # Check suites completed
        
        # GitHub-specific events
        'SponsorshipEvent',    # Sponsorship changes
        'MarketplacePurchaseEvent', # Marketplace purchases
    }
    filtered = [e for e in events if e.get("type") in wanted]
    log.info("Fetched %d relevant of %d total; poll interval: %ss", len(filtered), len(events), poll_interval)
    return filtered, new_etag or etag, poll_interval

def store_events(events: List[Dict]) -> int:
    if not events:
        return 0
    inserted = 0
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        for e in events:
            try:
                created_at = e["created_at"]
                created_ts = iso_to_epoch_s(created_at)
                cur.execute(
                    """
                    INSERT OR IGNORE INTO events
                    (id, type, actor_id, actor_login, repo_id, repo_name, created_at, created_at_ts, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        e["id"],
                        e["type"],
                        e["actor"]["id"] if e.get("actor") else None,
                        e["actor"]["login"] if e.get("actor") else None,
                        e["repo"]["id"] if e.get("repo") else None,
                        e["repo"]["name"] if e.get("repo") else None,
                        created_at,
                        created_ts,
                        json.dumps(e.get("payload", {})),
                    ),
                )
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as ex:
                log.warning("Failed to store event %s: %s", e.get("id"), ex)
        conn.commit()
    log.info("Stored %d new events", inserted)
    return inserted

def calculate_pr_metrics():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT repo_name, created_at_ts
            FROM events
            WHERE type = 'PullRequestEvent' AND repo_name IS NOT NULL
            ORDER BY repo_name, created_at_ts
            """
        )
        rows = cur.fetchall()
        if not rows:
            return
        by_repo: Dict[str, List[int]] = {}
        for repo, ts in rows:
            by_repo.setdefault(repo, []).append(ts)

        for repo, ts_list in by_repo.items():
            if len(ts_list) < 2:
                continue
            diffs = []
            prev = ts_list[0]
            for ts in ts_list[1:]:
                diffs.append((ts - prev) / 60.0)  # minutes
                prev = ts
            avg_minutes = sum(diffs) / len(diffs) if diffs else 0.0
            cur.execute(
                """
                INSERT INTO pr_metrics (repo_name, avg_time_between_prs_minutes, total_prs, last_updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(repo_name) DO UPDATE SET
                    avg_time_between_prs_minutes=excluded.avg_time_between_prs_minutes,
                    total_prs=excluded.total_prs,
                    last_updated=excluded.last_updated
                """,
                (repo, avg_minutes, len(ts_list), utc_now_iso()),
            )
        conn.commit()
    log.info("PR metrics updated")

def run_once(etag: Optional[str]) -> Optional[str]:
    events, etag, poll = fetch_events(etag)
    store_events(events)
    calculate_pr_metrics()
    return etag

def main():
    ensure_schema()
    etag: Optional[str] = None
    run_once_mode = ("--once" in os.sys.argv) or (os.environ.get("RUN_ONCE") == "1")
    if run_once_mode:
        run_once(etag)
        return

    log.info("Starting continuous monitor...")
    # Default fallback poll every 60s, but respect X-Poll-Interval when provided
    poll_interval = 60
    while True:
        try:
            events, etag, pi = fetch_events(etag)
            if pi:
                poll_interval = max(30, min(pi, 300))  # clamp 30..300s
            if store_events(events) > 0:
                calculate_pr_metrics()
        except Exception as ex:
            log.error("Monitor cycle error: %s", ex)
        time.sleep(poll_interval)

if __name__ == "__main__":
    main()
