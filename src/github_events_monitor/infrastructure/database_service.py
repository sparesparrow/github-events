"""
Database service that uses the abstract database interface.

This service provides a high-level interface for database operations
while maintaining compatibility with both SQLite and DynamoDB backends.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from .database_interface import DatabaseManager
from .database_factory import create_database_manager_from_config, DatabaseManagerSingleton
from ..config import config

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    High-level database service that abstracts database operations.
    
    This service uses the abstract database interface to provide a consistent
    API regardless of the underlying database provider (SQLite or DynamoDB).
    """
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None):
        if database_manager is None:
            # Create database manager from configuration
            db_config = config.get_database_config()
            self.db_manager = create_database_manager_from_config(db_config)
        else:
            self.db_manager = database_manager
    
    async def initialize(self) -> None:
        """Initialize the database service."""
        await self.db_manager.initialize()
        logger.info(f"Database service initialized with {type(self.db_manager).__name__}")
    
    async def close(self) -> None:
        """Close the database service."""
        await self.db_manager.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        return await self.db_manager.health_check()
    
    # Events operations
    async def store_events(self, events_data: List[Dict[str, Any]]) -> int:
        """Store multiple events."""
        return await self.db_manager.events.insert_events(events_data)
    
    async def get_events_by_type(
        self, 
        event_type: str,
        repo: Optional[str] = None,
        hours_back: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get events by type with optional filtering."""
        since_ts = None
        if hours_back:
            since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        return await self.db_manager.events.get_events_by_type(
            event_type=event_type,
            repo=repo,
            since_ts=since_ts,
            limit=limit
        )
    
    async def count_events_by_type(
        self, 
        hours_back: Optional[int] = None,
        repo: Optional[str] = None
    ) -> Dict[str, int]:
        """Count events by type with optional filtering."""
        since_ts = None
        if hours_back:
            since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        return await self.db_manager.events.count_events_by_type(
            since_ts=since_ts,
            repo=repo
        )
    
    async def get_trending_repositories(
        self, 
        hours_back: int = 24,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending repositories."""
        since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        return await self.db_manager.events.get_trending_repositories(
            since_ts=since_ts,
            limit=limit
        )
    
    async def get_repository_activity(
        self, 
        repo: str,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get repository activity."""
        since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        return await self.db_manager.events.get_repository_activity(
            repo=repo,
            since_ts=since_ts
        )
    
    # Commits operations
    async def store_commit(self, commit_data: Dict[str, Any]) -> bool:
        """Store a single commit."""
        return await self.db_manager.commits.insert_commit(commit_data)
    
    async def store_commit_files(
        self, 
        commit_sha: str,
        files_data: List[Dict[str, Any]]
    ) -> int:
        """Store file changes for a commit."""
        return await self.db_manager.commits.insert_commit_files(commit_sha, files_data)
    
    async def store_commit_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Store commit summary."""
        return await self.db_manager.commits.insert_commit_summary(summary_data)
    
    async def get_commit(self, sha: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get commit by SHA."""
        return await self.db_manager.commits.get_commit(sha, repo)
    
    async def get_commit_files(self, sha: str, repo: str) -> List[Dict[str, Any]]:
        """Get commit file changes."""
        return await self.db_manager.commits.get_commit_files(sha, repo)
    
    async def get_recent_commits(
        self, 
        repo: str,
        hours_back: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent commits."""
        since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        return await self.db_manager.commits.get_recent_commits(
            repo=repo,
            since_ts=since_ts,
            limit=limit
        )
    
    async def get_commits_by_author(
        self, 
        repo: str,
        hours_back: int = 168
    ) -> List[Dict[str, Any]]:
        """Get commits grouped by author."""
        since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        return await self.db_manager.commits.get_commits_by_author(
            repo=repo,
            since_ts=since_ts
        )
    
    async def get_high_impact_commits(
        self, 
        repo: str,
        hours_back: int = 168,
        min_impact_score: float = 70.0
    ) -> List[Dict[str, Any]]:
        """Get high-impact commits."""
        since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        return await self.db_manager.commits.get_high_impact_commits(
            repo=repo,
            since_ts=since_ts,
            min_impact_score=min_impact_score
        )
    
    # Metrics operations
    async def store_repository_health_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Store repository health metrics."""
        return await self.db_manager.metrics.upsert_repository_health_metrics(metrics_data)
    
    async def get_repository_health_metrics(self, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository health metrics."""
        return await self.db_manager.metrics.get_repository_health_metrics(repo)
    
    async def store_developer_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Store developer metrics."""
        return await self.db_manager.metrics.upsert_developer_metrics(metrics_data)
    
    async def get_developer_metrics(
        self, 
        repo: str,
        time_period: str = 'weekly',
        hours_back: int = 168
    ) -> List[Dict[str, Any]]:
        """Get developer metrics."""
        since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        return await self.db_manager.metrics.get_developer_metrics(
            repo=repo,
            time_period=time_period,
            since_ts=since_ts
        )
    
    async def store_security_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Store security metrics."""
        return await self.db_manager.metrics.upsert_security_metrics(metrics_data)
    
    async def get_security_metrics(
        self, 
        repo: str,
        hours_back: int = 168
    ) -> List[Dict[str, Any]]:
        """Get security metrics."""
        since_ts = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        return await self.db_manager.metrics.get_security_metrics(
            repo=repo,
            since_ts=since_ts
        )


# Singleton instance for application-wide use
_database_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get singleton database service instance."""
    global _database_service
    
    if _database_service is None:
        _database_service = DatabaseService()
    
    return _database_service


async def initialize_database_service() -> DatabaseService:
    """Initialize and return database service."""
    service = get_database_service()
    await service.initialize()
    return service


def reset_database_service() -> None:
    """Reset database service singleton (useful for testing)."""
    global _database_service
    _database_service = None