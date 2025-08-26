"""
Database Manager and Aggregator

Provides a single owner for the SQLite database file and re-exports all DAO
classes and the GitHub events collector from one place.
"""

import os
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

import aiosqlite

from .event import GitHubEvent


# -----------------------
# DAO layer (migrated)
# -----------------------

class EventsDao:
    """Base Data Access Object for GitHub Events."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.event_type = self._get_event_type()

    def _get_event_type(self) -> str:  # pragma: no cover - abstract by convention
        raise NotImplementedError

    async def _connect(self) -> aiosqlite.Connection:
        return await aiosqlite.connect(self.db_path)

    async def get(self, repo: Optional[str] = None, since_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def count_by_repo(self, repo: str, since_ts: datetime) -> int:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM events
                WHERE repo_name = ? AND event_type = ? AND created_at >= ?
                """,
                (repo, self.event_type, since_ts),
            )
            row = await cursor.fetchone()
            return int(row[0]) if row else 0
        finally:
            await db.close()


class WatchEventDao(EventsDao):
    def _get_event_type(self) -> str:
        return "WatchEvent"

    async def get(self, repo: Optional[str] = None, since_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            where: List[str] = ["event_type = ?"]
            params: List[Any] = [self.event_type]
            if repo is not None:
                where.append("repo_name = ?")
                params.append(repo)
            if since_ts is not None:
                where.append("created_at >= ?")
                params.append(since_ts)
            cursor = await db.execute(
                f"SELECT id, repo_name, actor_login, created_at, payload FROM events WHERE {' AND '.join(where)} ORDER BY created_at ASC",
                tuple(params),
            )
            rows = await cursor.fetchall()
            results: List[Dict[str, Any]] = []
            for eid, repo_name, actor_login, created_at, payload_str in rows:
                try:
                    results.append({
                        "id": eid,
                        "repo_name": repo_name,
                        "actor_login": actor_login,
                        "created_at": created_at,
                        "payload": json.loads(payload_str) if isinstance(payload_str, str) else payload_str,
                    })
                except Exception:
                    continue
            return results
        finally:
            await db.close()

    async def get_star_count_by_repo(self, repo: str, since_ts: datetime) -> int:
        return await self.count_by_repo(repo, since_ts)


class PullRequestEventDao(EventsDao):
    def _get_event_type(self) -> str:
        return "PullRequestEvent"

    async def get(self, repo: Optional[str] = None, since_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            where: List[str] = ["event_type = ?"]
            params: List[Any] = [self.event_type]
            if repo is not None:
                where.append("repo_name = ?")
                params.append(repo)
            if since_ts is not None:
                where.append("created_at >= ?")
                params.append(since_ts)
            cursor = await db.execute(
                f"SELECT id, repo_name, actor_login, created_at, payload FROM events WHERE {' AND '.join(where)} ORDER BY created_at ASC",
                tuple(params),
            )
            rows = await cursor.fetchall()
            results: List[Dict[str, Any]] = []
            for eid, repo_name, actor_login, created_at, payload_str in rows:
                try:
                    results.append({
                        "id": eid,
                        "repo_name": repo_name,
                        "actor_login": actor_login,
                        "created_at": created_at,
                        "payload": json.loads(payload_str) if isinstance(payload_str, str) else payload_str,
                    })
                except Exception:
                    continue
            return results
        finally:
            await db.close()

    async def get_pr_timestamps(self, repo: str) -> List[datetime]:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT created_at FROM events
                WHERE repo_name = ? AND event_type = ? AND json_extract(payload, '$.action') = 'opened'
                ORDER BY created_at ASC
                """,
                (repo, self.event_type),
            )
            rows = await cursor.fetchall()
            timestamps: List[datetime] = []
            for (created_at_str,) in rows:
                try:
                    timestamps.append(datetime.fromisoformat(str(created_at_str).replace('Z', '+00:00')))
                except Exception:
                    continue
            return timestamps
        finally:
            await db.close()

    async def get_pr_interval_stats(self, repo: str) -> Optional[Dict[str, Any]]:
        ts = await self.get_pr_timestamps(repo)
        if len(ts) < 2:
            return None
        intervals = [(ts[i] - ts[i-1]).total_seconds() for i in range(1, len(ts))]
        if not intervals:
            return None
        avg = sum(intervals) / len(intervals)
        return {
            "repo_name": repo,
            "pr_count": len(ts),
            "avg_interval_seconds": avg,
            "avg_interval_hours": avg / 3600,
            "min_interval_seconds": min(intervals),
            "max_interval_seconds": max(intervals),
        }

    async def get_pr_timeline(self, repo: str, days: int) -> List[Dict[str, Any]]:
        if days <= 0:
            days = 1
        now_utc = datetime.now(timezone.utc)
        cutoff_time = now_utc - timedelta(days=days)
        buckets: Dict[str, int] = {}
        for i in range(days + 1):
            day = (cutoff_time + timedelta(days=i)).date().isoformat()
            buckets[day] = 0
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT created_at, payload FROM events
                WHERE repo_name = ? AND event_type = 'PullRequestEvent' AND created_at >= ?
                ORDER BY created_at ASC
                """,
                (repo, cutoff_time),
            )
            rows = await cursor.fetchall()
            for created_at_str, payload_str in rows:
                try:
                    created_at = datetime.fromisoformat(str(created_at_str).replace('Z', '+00:00'))
                    payload = json.loads(payload_str)
                    if payload.get('action') == 'opened':
                        key = created_at.date().isoformat()
                        if key in buckets:
                            buckets[key] += 1
                except Exception:
                    continue
        finally:
            await db.close()
        return [{"date": d, "count": buckets[d]} for d in sorted(buckets.keys())]


class IssuesEventDao(EventsDao):
    def _get_event_type(self) -> str:
        return "IssuesEvent"

    async def get(self, repo: Optional[str] = None, since_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            where: List[str] = ["event_type = ?"]
            params: List[Any] = [self.event_type]
            if repo is not None:
                where.append("repo_name = ?")
                params.append(repo)
            if since_ts is not None:
                where.append("created_at >= ?")
                params.append(since_ts)
            cursor = await db.execute(
                f"SELECT id, repo_name, actor_login, created_at, payload FROM events WHERE {' AND '.join(where)} ORDER BY created_at ASC",
                tuple(params),
            )
            rows = await cursor.fetchall()
            results: List[Dict[str, Any]] = []
            for eid, repo_name, actor_login, created_at, payload_str in rows:
                try:
                    results.append({
                        "id": eid,
                        "repo_name": repo_name,
                        "actor_login": actor_login,
                        "created_at": created_at,
                        "payload": json.loads(payload_str) if isinstance(payload_str, str) else payload_str,
                    })
                except Exception:
                    continue
            return results
        finally:
            await db.close()

    async def get_issue_activity_summary(self, repo: str, since_ts: datetime) -> Dict[str, Any]:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT json_extract(payload, '$.action') as action, COUNT(*) as count
                FROM events WHERE repo_name = ? AND event_type = ? AND created_at >= ?
                GROUP BY json_extract(payload, '$.action') ORDER BY count DESC
                """,
                (repo, self.event_type, since_ts),
            )
            rows = await cursor.fetchall()
            activity: Dict[str, Any] = {}
            total = 0
            for action, count in rows:
                activity[action] = count
                total += count
            return {"total_issues": total, "activity": activity}
        finally:
            await db.close()


class EventsDaoFactory:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._daos: Dict[str, EventsDao] = {}

    def get_dao(self, event_type: str) -> EventsDao:
        if event_type not in self._daos:
            if event_type == "WatchEvent":
                self._daos[event_type] = WatchEventDao(self.db_path)
            elif event_type == "PullRequestEvent":
                self._daos[event_type] = PullRequestEventDao(self.db_path)
            elif event_type == "IssuesEvent":
                self._daos[event_type] = IssuesEventDao(self.db_path)
            else:
                raise ValueError(f"Unsupported event type: {event_type}")
        return self._daos[event_type]

    def get_watch_dao(self) -> WatchEventDao:
        return self.get_dao("WatchEvent")  # type: ignore

    def get_pr_dao(self) -> PullRequestEventDao:
        return self.get_dao("PullRequestEvent")  # type: ignore

    def get_issues_dao(self) -> IssuesEventDao:
        return self.get_dao("IssuesEvent")  # type: ignore


class SchemaDao:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self) -> None:
        db = await aiosqlite.connect(self.db_path)
        try:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    repo_name TEXT NOT NULL,
                    actor_login TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    payload TEXT NOT NULL,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_repo_name ON events(repo_name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_repo_type_created ON events(repo_name, event_type, created_at)")
            await db.commit()
        finally:
            await db.close()


class EventsWriteDao:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def insert_events(self, events: List[Dict[str, Any]]) -> int:
        if not events:
            return 0
        stored = 0
        db = await aiosqlite.connect(self.db_path)
        try:
            for event in events:
                try:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO events
                        (id, event_type, repo_name, actor_login, created_at, payload)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event["id"],
                            event["event_type"],
                            event["repo_name"],
                            event["actor_login"],
                            event["created_at"],
                            json.dumps(event["payload"]),
                        ),
                    )
                    if db.total_changes > 0:
                        stored += 1
                except Exception:
                    continue
            await db.commit()
        finally:
            await db.close()
        return stored


class AggregatesDao:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def _connect(self) -> aiosqlite.Connection:
        return await aiosqlite.connect(self.db_path)

    async def get_counts_by_type_since(self, since_ts: datetime) -> Dict[str, int]:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """SELECT event_type, COUNT(*) FROM events WHERE created_at >= ? GROUP BY event_type ORDER BY event_type""",
                (since_ts,),
            )
            rows = await cursor.fetchall()
            return {str(t): int(c) for t, c in rows}
        finally:
            await db.close()

    async def get_counts_by_type_total(self) -> Dict[str, int]:
        db = await self._connect()
        try:
            cursor = await db.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY event_type")
            rows = await cursor.fetchall()
            return {str(t): int(c) for t, c in rows}
        finally:
            await db.close()

    async def get_trending_since(self, since_ts: datetime, limit: int) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT repo_name,
                       COUNT(*) as total_events,
                       SUM(CASE WHEN event_type = 'WatchEvent' THEN 1 ELSE 0 END) as watch_events,
                       SUM(CASE WHEN event_type = 'PullRequestEvent' THEN 1 ELSE 0 END) as pr_events,
                       SUM(CASE WHEN event_type = 'IssuesEvent' THEN 1 ELSE 0 END) as issue_events,
                       MIN(created_at) as first_event,
                       MAX(created_at) as last_event
                FROM events WHERE created_at >= ? GROUP BY repo_name
                ORDER BY total_events DESC LIMIT ?
                """,
                (since_ts, limit),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "repo_name": r[0],
                    "total_events": r[1],
                    "watch_events": r[2],
                    "pr_events": r[3],
                    "issue_events": r[4],
                    "first_event": r[5],
                    "last_event": r[6],
                }
                for r in rows
            ]
        finally:
            await db.close()

    async def get_repository_activity_summary(self, repo: str, since_ts: datetime) -> Tuple[Dict[str, Any], int]:
        db = await self._connect()
        try:
            async def query(where: str, params: tuple) -> Tuple[Dict[str, Any], int]:
                cursor = await db.execute(
                    f"SELECT event_type, COUNT(*), MIN(created_at), MAX(created_at) FROM events WHERE {where} GROUP BY event_type ORDER BY COUNT(*) DESC",
                    params,
                )
                rows = await cursor.fetchall()
                activity: Dict[str, Any] = {}
                total = 0
                for et, count, first_ev, last_ev in rows:
                    activity[et] = {"count": count, "first_event": first_ev, "last_event": last_ev}
                    total += count
                return activity, total

            activity, total = await query("repo_name = ? AND created_at >= ?", (repo, since_ts))
            if total == 0:
                activity, total = await query("repo_name = ?", (repo,))
            return activity, total
        finally:
            await db.close()


class DatabaseManager:
    """Owns the SQLite database path and all DAOs for this app."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        resolved_path = (
            db_path
            or os.getenv("DATABASE_PATH")
            or "github_events.db"
        )
        self.db_path: str = resolved_path
        self.schema: SchemaDao = SchemaDao(self.db_path)
        self.writes: EventsWriteDao = EventsWriteDao(self.db_path)
        self.aggregates: AggregatesDao = AggregatesDao(self.db_path)
        self.events: EventsDaoFactory = EventsDaoFactory(self.db_path)

    async def initialize(self) -> None:
        """Create database file and schema as needed."""
        try:
            parent = Path(self.db_path).parent
            if str(parent) not in ("", ".") and not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Best effort
            pass
        await self.schema.initialize()

    # Convenience accessors
    def get_watch_dao(self) -> WatchEventDao:
        return self.events.get_watch_dao()

    def get_pr_dao(self) -> PullRequestEventDao:
        return self.events.get_pr_dao()

    def get_issues_dao(self) -> IssuesEventDao:
        return self.events.get_issues_dao()

    @classmethod
    def from_env(cls) -> "DatabaseManager":
        return cls(db_path=os.getenv("DATABASE_PATH", "github_events.db"))

    def __repr__(self) -> str:  # pragma: no cover
        return f"DatabaseManager(db_path={self.db_path!r})"


__all__ = [
    "DatabaseManager",
    "EventsDao",
    "WatchEventDao",
    "PullRequestEventDao",
    "IssuesEventDao",
    "EventsDaoFactory",
    "SchemaDao",
    "EventsWriteDao",
    "AggregatesDao",
]
