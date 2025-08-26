"""
Event model types.

Defines a lightweight base `Event` class and concrete `GitHubEvent` for use
throughout the monitor. Kept separate from database/collector logic to avoid
import cycles and to make modeling explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict


@dataclass
class Event:
    """Base event representation.

    Subclasses should extend the payload semantics as needed.
    """

    id: str
    event_type: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        return result


@dataclass
class GitHubEvent(Event):
    """Concrete GitHub Event with common fields used in this project."""

    repo_name: str
    actor_login: str
    payload: Dict[str, Any]

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> "GitHubEvent":
        return cls(
            id=data["id"],
            event_type=data["type"],
            repo_name=data["repo"]["name"],
            actor_login=data["actor"]["login"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            payload=data.get("payload", {}),
        )


# Optional: semantic subclasses for clarity (no extra behavior for now)
class WatchEvent(GitHubEvent):
    pass


class PullRequestEvent(GitHubEvent):
    pass


class IssuesEvent(GitHubEvent):
    pass


