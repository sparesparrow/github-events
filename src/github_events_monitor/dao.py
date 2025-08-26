"""
GitHub Events Monitor - Data Access Objects (DAO)

DAO layer for type-specific data access operations:
- EventsDao: Base class for all event data access
- WatchEventDao: WatchEvent-specific operations
- PullRequestEventDao: PullRequestEvent-specific operations  
- IssuesEventDao: IssuesEvent-specific operations
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

import aiosqlite

logger = logging.getLogger(__name__)


class EventsDao(ABC):
    """Base Data Access Object for GitHub Events"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.event_type = self._get_event_type()
    
    @abstractmethod
    def _get_event_type(self) -> str:
        """Return the event type this DAO handles"""
        pass
    
    @abstractmethod
    async def get(self, repo: Optional[str] = None, since_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Return raw events for this type with optional filters."""
        pass
    
    async def _connect(self) -> aiosqlite.Connection:
        """Get database connection"""
        return await aiosqlite.connect(self.db_path)
    
    async def count_by_repo(self, repo: str, since_ts: datetime) -> int:
        """Count events of this type for a specific repository since timestamp"""
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT COUNT(*) 
                FROM events 
                WHERE repo_name = ? 
                  AND event_type = ? 
                  AND created_at >= ?
                """,
                (repo, self.event_type, since_ts),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
        finally:
            await db.close()
    
    async def count_total(self, since_ts: datetime) -> int:
        """Count total events of this type since timestamp"""
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT COUNT(*) 
                FROM events 
                WHERE event_type = ? 
                  AND created_at >= ?
                """,
                (self.event_type, since_ts),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
        finally:
            await db.close()


class WatchEventDao(EventsDao):
    """Data Access Object for WatchEvent operations"""
    
    def _get_event_type(self) -> str:
        return "WatchEvent"
    
    async def get(self, repo: Optional[str] = None, since_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            where_clauses = ["event_type = ?"]
            params: List[Any] = [self.event_type]
            if repo is not None:
                where_clauses.append("repo_name = ?")
                params.append(repo)
            if since_ts is not None:
                where_clauses.append("created_at >= ?")
                params.append(since_ts)
            where_sql = " AND ".join(where_clauses)
            cursor = await db.execute(
                f"""
                SELECT id, repo_name, actor_login, created_at, payload
                FROM events
                WHERE {where_sql}
                ORDER BY created_at ASC
                """,
                tuple(params),
            )
            rows = await cursor.fetchall()
            results: List[Dict[str, Any]] = []
            for (eid, repo_name, actor_login, created_at, payload_str) in rows:
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
        """Get count of stars (watch events) for a repository"""
        return await self.count_by_repo(repo, since_ts)
    
    async def get_top_starred_repos(self, since_ts: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        """Get repositories with most stars in time period"""
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT repo_name, COUNT(*) as star_count
                FROM events 
                WHERE event_type = ? 
                  AND created_at >= ?
                GROUP BY repo_name
                ORDER BY star_count DESC
                LIMIT ?
                """,
                (self.event_type, since_ts, limit),
            )
            rows = await cursor.fetchall()
            
            repos = []
            for repo_name, star_count in rows:
                repos.append({
                    "repo_name": repo_name,
                    "star_count": star_count
                })
            
            return repos
        finally:
            await db.close()


class PullRequestEventDao(EventsDao):
    """Data Access Object for PullRequestEvent operations"""
    
    def _get_event_type(self) -> str:
        return "PullRequestEvent"
    
    async def get(self, repo: Optional[str] = None, since_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            where_clauses = ["event_type = ?"]
            params: List[Any] = [self.event_type]
            if repo is not None:
                where_clauses.append("repo_name = ?")
                params.append(repo)
            if since_ts is not None:
                where_clauses.append("created_at >= ?")
                params.append(since_ts)
            where_sql = " AND ".join(where_clauses)
            cursor = await db.execute(
                f"""
                SELECT id, repo_name, actor_login, created_at, payload
                FROM events
                WHERE {where_sql}
                ORDER BY created_at ASC
                """,
                tuple(params),
            )
            rows = await cursor.fetchall()
            results: List[Dict[str, Any]] = []
            for (eid, repo_name, actor_login, created_at, payload_str) in rows:
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
        """Get timestamps of opened PR events for a repository"""
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT created_at
                FROM events
                WHERE repo_name = ?
                  AND event_type = ?
                  AND json_extract(payload, '$.action') = 'opened'
                ORDER BY created_at ASC
                """,
                (repo, self.event_type),
            )
            rows = await cursor.fetchall()
            
            timestamps = []
            for (created_at_str,) in rows:
                try:
                    timestamp = datetime.fromisoformat(str(created_at_str).replace('Z', '+00:00'))
                    timestamps.append(timestamp)
                except Exception:
                    continue
            
            return timestamps
        finally:
            await db.close()
    
    async def get_pr_interval_stats(self, repo: str) -> Optional[Dict[str, Any]]:
        """Calculate PR interval statistics for a repository"""
        timestamps = await self.get_pr_timestamps(repo)
        
        if len(timestamps) < 2:
            return None
        
        # Calculate intervals between consecutive PRs
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        if not intervals:
            return None
        
        # Calculate statistics
        avg_interval_seconds = sum(intervals) / len(intervals)
        avg_interval_hours = avg_interval_seconds / 3600
        
        return {
            "repo_name": repo,
            "pr_count": len(timestamps),
            "avg_interval_seconds": avg_interval_seconds,
            "avg_interval_hours": avg_interval_hours,
            "min_interval_seconds": min(intervals),
            "max_interval_seconds": max(intervals)
        }

    async def get_pr_timeline(self, repo: str, days: int) -> List[Dict[str, Any]]:
        """Return per-day counts of 'opened' PR events for a repository over the last N days."""
        if days <= 0:
            days = 1
        now_utc = datetime.now(timezone.utc)
        cutoff_time = now_utc - timedelta(days=days)
        # Build zero-filled buckets
        buckets: Dict[str, int] = {}
        for i in range(days + 1):
            day = (cutoff_time + timedelta(days=i)).date().isoformat()
            buckets[day] = 0
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT created_at, payload
                FROM events
                WHERE repo_name = ?
                  AND event_type = 'PullRequestEvent'
                  AND created_at >= ?
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
                        day_key = created_at.date().isoformat()
                        if day_key in buckets:
                            buckets[day_key] += 1
                except Exception:
                    continue
        finally:
            await db.close()
        return [{"date": day, "count": buckets[day]} for day in sorted(buckets.keys())]


class IssuesEventDao(EventsDao):
    """Data Access Object for IssuesEvent operations"""
    
    def _get_event_type(self) -> str:
        return "IssuesEvent"
    
    async def get(self, repo: Optional[str] = None, since_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            where_clauses = ["event_type = ?"]
            params: List[Any] = [self.event_type]
            if repo is not None:
                where_clauses.append("repo_name = ?")
                params.append(repo)
            if since_ts is not None:
                where_clauses.append("created_at >= ?")
                params.append(since_ts)
            where_sql = " AND ".join(where_clauses)
            cursor = await db.execute(
                f"""
                SELECT id, repo_name, actor_login, created_at, payload
                FROM events
                WHERE {where_sql}
                ORDER BY created_at ASC
                """,
                tuple(params),
            )
            rows = await cursor.fetchall()
            results: List[Dict[str, Any]] = []
            for (eid, repo_name, actor_login, created_at, payload_str) in rows:
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
        """Get issue activity summary for a repository"""
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT 
                    json_extract(payload, '$.action') as action,
                    COUNT(*) as count
                FROM events
                WHERE repo_name = ?
                  AND event_type = ?
                  AND created_at >= ?
                GROUP BY json_extract(payload, '$.action')
                ORDER BY count DESC
                """,
                (repo, self.event_type, since_ts),
            )
            rows = await cursor.fetchall()
            
            activity = {}
            total_issues = 0
            for action, count in rows:
                activity[action] = count
                total_issues += count
            
            return {
                "total_issues": total_issues,
                "activity": activity
            }
        finally:
            await db.close()


class EventsDaoFactory:
    """Factory for creating DAO instances"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._daos = {}
    
    def get_dao(self, event_type: str) -> EventsDao:
        """Get DAO instance for the specified event type"""
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
        """Get WatchEvent DAO"""
        return self.get_dao("WatchEvent")
    
    def get_pr_dao(self) -> PullRequestEventDao:
        """Get PullRequestEvent DAO"""
        return self.get_dao("PullRequestEvent")
    
    def get_issues_dao(self) -> IssuesEventDao:
        """Get IssuesEvent DAO"""
        return self.get_dao("IssuesEvent")
    
    def get_all_daos(self) -> Dict[str, EventsDao]:
        """Get all DAO instances"""
        return {
            "WatchEvent": self.get_watch_dao(),
            "PullRequestEvent": self.get_pr_dao(),
            "IssuesEvent": self.get_issues_dao()
        }


class SchemaDao:
    """DAO responsible for database schema initialization and migrations."""
    
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
            # Defensive migrations
            try:
                await db.execute("ALTER TABLE events ADD COLUMN event_type TEXT")
            except Exception:
                pass
            try:
                await db.execute("UPDATE events SET event_type = COALESCE(event_type, type)")
            except Exception:
                pass
            # Indices
            await db.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_repo_name ON events(repo_name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_repo_type_created ON events(repo_name, event_type, created_at)")
            await db.commit()
        finally:
            await db.close()


class EventsWriteDao:
    """DAO responsible for write operations to events table."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def insert_events(self, events: List[Dict[str, Any]]) -> int:
        """Insert events with INSERT OR IGNORE semantics, returns number of new rows."""
        if not events:
            return 0
        stored_count = 0
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
                        stored_count += 1
                except Exception as e:
                    logger.error(f"Failed to store event {event.get('id')}: {e}")
            await db.commit()
        finally:
            await db.close()
        return stored_count


class AggregatesDao:
    """DAO for cross-type aggregate queries and health checks."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def _connect(self) -> aiosqlite.Connection:
        return await aiosqlite.connect(self.db_path)
    
    async def get_total_events(self) -> int:
        db = await self._connect()
        try:
            cursor = await db.execute("SELECT COUNT(*) FROM events")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0
        finally:
            await db.close()
    
    async def get_counts_by_type_since(self, since_ts: datetime) -> Dict[str, int]:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM events 
                WHERE created_at >= ? 
                GROUP BY event_type
                ORDER BY event_type
                """,
                (since_ts,),
            )
            rows = await cursor.fetchall()
            counts: Dict[str, int] = {}
            for event_type, count in rows:
                counts[str(event_type)] = int(count)
            return counts
        finally:
            await db.close()
    
    async def get_counts_by_type_total(self) -> Dict[str, int]:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM events 
                GROUP BY event_type
                ORDER BY event_type
                """
            )
            rows = await cursor.fetchall()
            counts: Dict[str, int] = {}
            for event_type, count in rows:
                counts[str(event_type)] = int(count)
            return counts
        finally:
            await db.close()
    
    async def get_trending_since(self, since_ts: datetime, limit: int) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT 
                    repo_name,
                    COUNT(*) as total_events,
                    SUM(CASE WHEN event_type = 'WatchEvent' THEN 1 ELSE 0 END) as watch_events,
                    SUM(CASE WHEN event_type = 'PullRequestEvent' THEN 1 ELSE 0 END) as pr_events,
                    SUM(CASE WHEN event_type = 'IssuesEvent' THEN 1 ELSE 0 END) as issue_events,
                    MIN(created_at) as first_event,
                    MAX(created_at) as last_event
                FROM events
                WHERE created_at >= ?
                GROUP BY repo_name
                ORDER BY total_events DESC
                LIMIT ?
                """,
                (since_ts, limit),
            )
            rows = await cursor.fetchall()
            repositories: List[Dict[str, Any]] = []
            for row in rows:
                repo_name, total_events, watch_events, pr_events, issue_events, first_event, last_event = row
                repositories.append({
                    "repo_name": repo_name,
                    "total_events": total_events,
                    "watch_events": watch_events,
                    "pr_events": pr_events,
                    "issue_events": issue_events,
                    "first_event": first_event,
                    "last_event": last_event
                })
            return repositories
        finally:
            await db.close()
    
    async def get_repository_activity_summary(self, repo: str, since_ts: datetime) -> Tuple[Dict[str, Any], int]:
        db = await self._connect()
        try:
            async def query_activity(where_clause: str, params: tuple) -> Tuple[Dict[str, Any], int]:
                cursor = await db.execute(
                    f"""
                    SELECT 
                        event_type,
                        COUNT(*) as count,
                        MIN(created_at) as first_event,
                        MAX(created_at) as last_event
                    FROM events
                    WHERE {where_clause}
                    GROUP BY event_type
                    ORDER BY count DESC
                    """,
                    params,
                )
                rows = await cursor.fetchall()
                activity_local: Dict[str, Any] = {}
                total_local = 0
                for event_type, count, first_event, last_event in rows:
                    activity_local[event_type] = {
                        "count": count,
                        "first_event": first_event,
                        "last_event": last_event,
                    }
                    total_local += count
                return activity_local, total_local
            activity, total_events = await query_activity("repo_name = ? AND created_at >= ?", (repo, since_ts))
            if total_events == 0:
                activity, total_events = await query_activity("repo_name = ?", (repo,))
            return activity, total_events
        finally:
            await db.close()
    
    async def get_event_counts_timeseries(self, since_ts: datetime) -> List[Dict[str, Any]]:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT
                    strftime('%Y-%m-%dT%H:%M:00Z', created_at) as minute_bucket,
                    COUNT(*) as total
                FROM events
                WHERE created_at >= ?
                GROUP BY minute_bucket
                ORDER BY minute_bucket ASC
                """,
                (since_ts,),
            )
            rows = await cursor.fetchall()
            return [{"bucket_start": b, "total": t} for b, t in rows]
        finally:
            await db.close()
