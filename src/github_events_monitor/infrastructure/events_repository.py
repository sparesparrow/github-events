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
