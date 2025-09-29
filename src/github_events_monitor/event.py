"""
Event models.

Defines `GitHubEvent` (and semantic subclasses) used across the monitor.
Kept separate from DB/collector logic to avoid cycles and for clarity.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict


@dataclass
class GitHubEvent:
    """Concrete GitHub Event with common fields used in this project.

    Note: Flat data structure (no base class inheritance).
    """

    id: str
    event_type: str
    created_at: datetime
    repo_name: str
    actor_login: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        return result

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


class WatchEvent(GitHubEvent):
    event_type = "WatchEvent"


class PullRequestEvent(GitHubEvent):
    event_type = "PullRequestEvent"


class IssuesEvent(GitHubEvent):
    event_type = "IssuesEvent"


class PushEvent(GitHubEvent):
    event_type = "PushEvent"


class ForkEvent(GitHubEvent):
    event_type = "ForkEvent"


class CreateEvent(GitHubEvent):
    event_type = "CreateEvent"


class DeleteEvent(GitHubEvent):
    event_type = "DeleteEvent"


class ReleaseEvent(GitHubEvent):
    event_type = "ReleaseEvent"


class CommitCommentEvent(GitHubEvent):
    event_type = "CommitCommentEvent"


class IssueCommentEvent(GitHubEvent):
    event_type = "IssueCommentEvent"


class PullRequestReviewEvent(GitHubEvent):
    event_type = "PullRequestReviewEvent"


class PullRequestReviewCommentEvent(GitHubEvent):
    event_type = "PullRequestReviewCommentEvent"


class PublicEvent(GitHubEvent):
    event_type = "PublicEvent"


class MemberEvent(GitHubEvent):
    event_type = "MemberEvent"


class TeamAddEvent(GitHubEvent):
    event_type = "TeamAddEvent"


class GollumEvent(GitHubEvent):
    event_type = "GollumEvent"


class DeploymentEvent(GitHubEvent):
    event_type = "DeploymentEvent"


class DeploymentStatusEvent(GitHubEvent):
    event_type = "DeploymentStatusEvent"


class StatusEvent(GitHubEvent):
    event_type = "StatusEvent"


class CheckRunEvent(GitHubEvent):
    event_type = "CheckRunEvent"


class CheckSuiteEvent(GitHubEvent):
    event_type = "CheckSuiteEvent"


class SponsorshipEvent(GitHubEvent):
    event_type = "SponsorshipEvent"


class MarketplacePurchaseEvent(GitHubEvent):
    event_type = "MarketplacePurchaseEvent"
