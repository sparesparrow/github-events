"""
Database abstraction layer following SOLID principles.

This module defines abstract interfaces for database operations,
allowing different database implementations (SQLite, DynamoDB, etc.)
to be used interchangeably.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol, Union
from datetime import datetime
from enum import Enum


class DatabaseProvider(Enum):
    """Supported database providers."""
    SQLITE = "sqlite"
    DYNAMODB = "dynamodb"


class DatabaseConnection(ABC):
    """Abstract base class for database connections."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the database connection and create necessary tables/indexes."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check database health and return status information."""
        pass


class EventsRepository(ABC):
    """Abstract repository for events operations."""
    
    @abstractmethod
    async def insert_event(self, event_data: Dict[str, Any]) -> bool:
        """Insert a single event. Returns True if successful."""
        pass
    
    @abstractmethod
    async def insert_events(self, events_data: List[Dict[str, Any]]) -> int:
        """Insert multiple events. Returns number of successfully inserted events."""
        pass
    
    @abstractmethod
    async def get_events_by_type(
        self, 
        event_type: str, 
        repo: Optional[str] = None,
        since_ts: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get events by type with optional filtering."""
        pass
    
    @abstractmethod
    async def count_events_by_type(
        self, 
        since_ts: Optional[datetime] = None,
        repo: Optional[str] = None
    ) -> Dict[str, int]:
        """Count events by type with optional filtering."""
        pass
    
    @abstractmethod
    async def get_trending_repositories(
        self, 
        since_ts: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending repositories based on event activity."""
        pass
    
    @abstractmethod
    async def get_repository_activity(
        self, 
        repo: str,
        since_ts: datetime
    ) -> Dict[str, Any]:
        """Get activity summary for a specific repository."""
        pass


class CommitsRepository(ABC):
    """Abstract repository for commits operations."""
    
    @abstractmethod
    async def insert_commit(self, commit_data: Dict[str, Any]) -> bool:
        """Insert a single commit."""
        pass
    
    @abstractmethod
    async def insert_commit_files(
        self, 
        commit_sha: str,
        files_data: List[Dict[str, Any]]
    ) -> int:
        """Insert file changes for a commit."""
        pass
    
    @abstractmethod
    async def insert_commit_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Insert commit summary and analysis."""
        pass
    
    @abstractmethod
    async def get_commit(self, sha: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get commit by SHA and repository."""
        pass
    
    @abstractmethod
    async def get_commit_files(self, sha: str, repo: str) -> List[Dict[str, Any]]:
        """Get file changes for a commit."""
        pass
    
    @abstractmethod
    async def get_recent_commits(
        self, 
        repo: str,
        since_ts: datetime,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent commits for a repository."""
        pass
    
    @abstractmethod
    async def get_commits_by_author(
        self, 
        repo: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get commit statistics grouped by author."""
        pass
    
    @abstractmethod
    async def get_high_impact_commits(
        self, 
        repo: str,
        since_ts: datetime,
        min_impact_score: float = 70.0
    ) -> List[Dict[str, Any]]:
        """Get high-impact commits."""
        pass


class MetricsRepository(ABC):
    """Abstract repository for metrics and aggregated data."""
    
    @abstractmethod
    async def upsert_repository_health_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Insert or update repository health metrics."""
        pass
    
    @abstractmethod
    async def get_repository_health_metrics(self, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository health metrics."""
        pass
    
    @abstractmethod
    async def upsert_developer_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Insert or update developer metrics."""
        pass
    
    @abstractmethod
    async def get_developer_metrics(
        self, 
        repo: str,
        time_period: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get developer metrics."""
        pass
    
    @abstractmethod
    async def upsert_security_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Insert or update security metrics."""
        pass
    
    @abstractmethod
    async def get_security_metrics(
        self, 
        repo: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get security metrics."""
        pass


class DatabaseManager(ABC):
    """Abstract database manager that coordinates all repositories."""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
    
    @property
    @abstractmethod
    def events(self) -> EventsRepository:
        """Get events repository."""
        pass
    
    @property
    @abstractmethod
    def commits(self) -> CommitsRepository:
        """Get commits repository."""
        pass
    
    @property
    @abstractmethod
    def metrics(self) -> MetricsRepository:
        """Get metrics repository."""
        pass
    
    async def initialize(self) -> None:
        """Initialize the database manager."""
        await self.connection.initialize()
    
    async def close(self) -> None:
        """Close the database manager."""
        await self.connection.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        return await self.connection.health_check()


class DatabaseFactory(ABC):
    """Abstract factory for creating database managers."""
    
    @staticmethod
    @abstractmethod
    def create_database_manager(
        provider: DatabaseProvider,
        connection_config: Dict[str, Any]
    ) -> DatabaseManager:
        """Create a database manager for the specified provider."""
        pass


# Type aliases for better readability
EventData = Dict[str, Any]
CommitData = Dict[str, Any]
MetricsData = Dict[str, Any]
QueryFilter = Dict[str, Any]