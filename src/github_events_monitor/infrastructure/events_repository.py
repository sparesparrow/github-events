from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from src.github_events_monitor.domain.protocols import EventReaderProtocol
from src.github_events_monitor.infrastructure.db_connection import DBConnection


class EventsRepository(EventReaderProtocol):
    def __init__(self, db: DBConnection) -> None:
        self.db = db

    async def count_events_by_type(self, since_ts: int, repo: Optional[str] = None) -> Dict[str, int]:
        async with await self.db.connect() as conn:
            if repo:
                q = "SELECT event_type, COUNT(*) FROM events WHERE created_at_ts >= ? AND repo_name = ? GROUP BY event_type"
                args = (since_ts, repo)
            else:
                q = "SELECT event_type, COUNT(*) FROM events WHERE created_at_ts >= ? GROUP BY event_type"
                args = (since_ts,)
            async with conn.execute(q, args) as cur:
                rows = await cur.fetchall()
        return {row[0]: int(row[1]) for row in rows}

    async def pr_timestamps(self, repo: str) -> List[int]:
        # Focus on PR opened events
        async with await self.db.connect() as conn:
            q = """
            SELECT created_at_ts
            FROM events
            WHERE event_type = 'PullRequestEvent' AND repo_name = ?
            ORDER BY created_at_ts ASC
            """
            async with conn.execute(q, (repo,)) as cur:
                rows = await cur.fetchall()
        return [int(row[0]) for row in rows]

    async def activity_by_repo(self, repo: str, since_ts: int) -> Dict[str, int]:
        return await self.count_events_by_type(since_ts=since_ts, repo=repo)

    async def trending_since(self, since_ts: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with await self.db.connect() as conn:
            q = """
            SELECT repo_name, COUNT(*) AS c
            FROM events
            WHERE created_at_ts >= ? AND repo_name IS NOT NULL
            GROUP BY repo_name
            ORDER BY c DESC
            LIMIT ?
            """
            async with conn.execute(q, (since_ts, limit)) as cur:
                rows = await cur.fetchall()
        return [{"repo_name": row[0], "count": int(row[1])} for row in rows]

    async def event_counts_timeseries(self, since_ts: int, bucket_minutes: int, repo: Optional[str] = None) -> List[Dict[str, Any]]:
        # Build buckets from since_ts to now in bucket_minutes increments
        now_ts = int(datetime.now(tz=timezone.utc).timestamp())
        bucket_sec = max(bucket_minutes, 1) * 60
        buckets = list(range(since_ts, now_ts + 1, bucket_sec))
        res: List[Dict[str, Any]] = []
        async with await self.db.connect() as conn:
            for i in range(len(buckets) - 1):
                start = buckets[i]
                end = buckets[i + 1]
                if repo:
                    q = """
                    SELECT event_type, COUNT(*)
                    FROM events
                    WHERE created_at_ts >= ? AND created_at_ts < ? AND repo_name = ?
                    GROUP BY event_type
                    """
                    args = (start, end, repo)
                else:
                    q = """
                    SELECT event_type, COUNT(*)
                    FROM events
                    WHERE created_at_ts >= ? AND created_at_ts < ?
                    GROUP BY event_type
                    """
                    args = (start, end)
                async with conn.execute(q, args) as cur:
                    rows = await cur.fetchall()
                res.append({"start_ts": start, "end_ts": end, "counts": {row[0]: int(row[1]) for row in rows}})
        return res

    # ------------------------------
    # Extended monitoring use-cases
    # ------------------------------

    async def _count_event_type(self, since_ts: int, event_type: str, repo: Optional[str] = None, action: Optional[str] = None) -> int:
        async with await self.db.connect() as conn:
            if repo:
                if action is not None:
                    q = """
                    SELECT COUNT(*) FROM events
                    WHERE created_at_ts >= ? AND repo_name = ? AND event_type = ?
                      AND json_extract(payload, '$.action') = ?
                    """
                    args = (since_ts, repo, event_type, action)
                else:
                    q = """
                    SELECT COUNT(*) FROM events
                    WHERE created_at_ts >= ? AND repo_name = ? AND event_type = ?
                    """
                    args = (since_ts, repo, event_type)
            else:
                if action is not None:
                    q = """
                    SELECT COUNT(*) FROM events
                    WHERE created_at_ts >= ? AND event_type = ?
                      AND json_extract(payload, '$.action') = ?
                    """
                    args = (since_ts, event_type, action)
                else:
                    q = """
                    SELECT COUNT(*) FROM events
                    WHERE created_at_ts >= ? AND event_type = ?
                    """
                    args = (since_ts, event_type)
            async with conn.execute(q, args) as cur:
                row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def _sum_json_int(self, since_ts: int, event_type: str, json_path: str, repo: Optional[str] = None) -> int:
        async with await self.db.connect() as conn:
            if repo:
                q = """
                SELECT COALESCE(SUM(CAST(json_extract(payload, ?) AS INTEGER)), 0)
                FROM events
                WHERE created_at_ts >= ? AND repo_name = ? AND event_type = ?
                """
                args = (json_path, since_ts, repo, event_type)
            else:
                q = """
                SELECT COALESCE(SUM(CAST(json_extract(payload, ?) AS INTEGER)), 0)
                FROM events
                WHERE created_at_ts >= ? AND event_type = ?
                """
                args = (json_path, since_ts, event_type)
            async with conn.execute(q, args) as cur:
                row = await cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    async def stars_since(self, since_ts: int, repo: Optional[str] = None) -> int:
        # WatchEvent typically has action 'started'; count either way
        count = await self._count_event_type(since_ts=since_ts, event_type="WatchEvent", repo=repo)
        return count

    async def releases_since(self, since_ts: int, repo: Optional[str] = None) -> int:
        # Only count published releases
        return await self._count_event_type(since_ts=since_ts, event_type="ReleaseEvent", repo=repo, action="published")

    async def push_activity_since(self, since_ts: int, repo: Optional[str] = None) -> Dict[str, int]:
        pushes = await self._count_event_type(since_ts=since_ts, event_type="PushEvent", repo=repo)
        commits = await self._sum_json_int(since_ts=since_ts, event_type="PushEvent", json_path="$.size", repo=repo)
        return {"push_events": pushes, "total_commits": commits}

    async def pr_merge_time_seconds(self, repo: str, since_ts: int) -> List[int]:
        # Compute per-PR merge durations for PRs opened since since_ts
        async with await self.db.connect() as conn:
            q = """
            WITH opens AS (
                SELECT CAST(json_extract(payload, '$.pull_request.number') AS INTEGER) AS pr_num,
                       MIN(created_at_ts) AS opened_ts
                FROM events
                WHERE repo_name = ?
                  AND event_type = 'PullRequestEvent'
                  AND created_at_ts >= ?
                  AND json_extract(payload, '$.action') = 'opened'
                GROUP BY pr_num
            ), merges AS (
                SELECT CAST(json_extract(payload, '$.pull_request.number') AS INTEGER) AS pr_num,
                       MIN(created_at_ts) AS merged_ts
                FROM events
                WHERE repo_name = ?
                  AND event_type = 'PullRequestEvent'
                  AND json_extract(payload, '$.action') = 'closed'
                  AND json_extract(payload, '$.pull_request.merged') = 1
                GROUP BY pr_num
            )
            SELECT m.merged_ts - o.opened_ts AS seconds
            FROM opens o
            JOIN merges m ON m.pr_num = o.pr_num
            WHERE m.merged_ts >= o.opened_ts
            """
            async with conn.execute(q, (repo, since_ts, repo)) as cur:
                rows = await cur.fetchall()
        return [int(r[0]) for r in rows if r and r[0] is not None and int(r[0]) >= 0]

    async def issue_first_response_seconds(self, repo: str, since_ts: int) -> List[int]:
        async with await self.db.connect() as conn:
            q = """
            WITH openings AS (
                SELECT CAST(json_extract(payload, '$.issue.number') AS INTEGER) AS issue_num,
                       MIN(created_at_ts) AS opened_ts
                FROM events
                WHERE repo_name = ?
                  AND event_type = 'IssuesEvent'
                  AND created_at_ts >= ?
                  AND json_extract(payload, '$.action') = 'opened'
                GROUP BY issue_num
            ), first_comments AS (
                SELECT CAST(json_extract(payload, '$.issue.number') AS INTEGER) AS issue_num,
                       MIN(created_at_ts) AS first_comment_ts
                FROM events
                WHERE repo_name = ?
                  AND event_type = 'IssueCommentEvent'
                GROUP BY issue_num
            )
            SELECT c.first_comment_ts - o.opened_ts AS seconds
            FROM openings o
            JOIN first_comments c ON c.issue_num = o.issue_num
            WHERE c.first_comment_ts >= o.opened_ts
            """
            async with conn.execute(q, (repo, since_ts, repo)) as cur:
                rows = await cur.fetchall()
        return [int(r[0]) for r in rows if r and r[0] is not None and int(r[0]) >= 0]
