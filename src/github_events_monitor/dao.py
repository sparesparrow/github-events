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


class IssuesEventDao(EventsDao):
    """Data Access Object for IssuesEvent operations"""
    
    def _get_event_type(self) -> str:
        return "IssuesEvent"
    
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
