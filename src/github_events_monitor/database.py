"""
Database Manager and Aggregator

Provides a single owner for the SQLite database file and re-exports all DAO
classes and the GitHub events collector from one place.
"""

import os
from pathlib import Path
from typing import Optional

from .dao import (
    EventsDao,
    WatchEventDao,
    PullRequestEventDao,
    IssuesEventDao,
    EventsDaoFactory,
    SchemaDao,
    EventsWriteDao,
    AggregatesDao,
)
from .collector import (
    GitHubEventsCollector,
    GitHubEvent,
    get_collector,
)


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
    # Manager
    "DatabaseManager",
    # DAOs
    "EventsDao",
    "WatchEventDao",
    "PullRequestEventDao",
    "IssuesEventDao",
    "EventsDaoFactory",
    "SchemaDao",
    "EventsWriteDao",
    "AggregatesDao",
    # Collector
    "GitHubEventsCollector",
    "GitHubEvent",
    "get_collector",
]
