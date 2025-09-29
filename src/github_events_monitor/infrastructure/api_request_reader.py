from __future__ import annotations
import os
from datetime import datetime
from typing import Iterable, List, Optional

import httpx

from src.github_events_monitor.domain.events import GitHubEvent

GITHUB_EVENTS_URL = "https://api.github.com/events"
GITHUB_REPO_EVENTS_URL = "https://api.github.com/repos/{repo}/events"
# Expanded list of GitHub events we care about for monitoring use-cases
INTERESTED_TYPES = {
    "WatchEvent",                     # Stars
    "PullRequestEvent",               # PR open/close/merge
    "IssuesEvent",                    # Issues open/close/etc
    "IssueCommentEvent",              # First response time, engagement
    "PushEvent",                      # Commit and push activity
    "ReleaseEvent",                   # Releases published
    "PullRequestReviewEvent",         # Review activity
    "PullRequestReviewCommentEvent",  # Review comments
    "ForkEvent",                      # Fork activity
    "CreateEvent",                    # Branch/repo creation
    "DeleteEvent",                    # Branch deletion
}


class ApiRequestReader:
    def __init__(self, github_token: Optional[str] = None, user_agent: str = "github-events-monitor") -> None:
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.user_agent = user_agent

    def _headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": self.user_agent}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    async def fetch_global_events(self, limit: int = 100) -> List[GitHubEvent]:
        async with httpx.AsyncClient(timeout=30.0, headers=self._headers()) as client:
            r = await client.get(GITHUB_EVENTS_URL, params={"per_page": min(max(limit, 1), 100)})
            r.raise_for_status()
            data = r.json()
        return self._normalize(data)

    async def fetch_repo_events(self, repo: str, limit: int = 100) -> List[GitHubEvent]:
        url = GITHUB_REPO_EVENTS_URL.format(repo=repo)
        async with httpx.AsyncClient(timeout=30.0, headers=self._headers()) as client:
            r = await client.get(url, params={"per_page": min(max(limit, 1), 100)})
            r.raise_for_status()
            data = r.json()
        return self._normalize(data)

    def _normalize(self, raw: Iterable[dict]) -> List[GitHubEvent]:
        events: List[GitHubEvent] = []
        for item in raw:
            etype = item.get("type")
            if etype not in INTERESTED_TYPES:
                continue
            rid = str(item.get("id"))
            created = item.get("created_at")
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")) if created else datetime.utcnow()
            repo_name = (item.get("repo") or {}).get("name")
            actor_login = (item.get("actor") or {}).get("login")
            payload = item.get("payload") or {}
            events.append(GitHubEvent(id=rid, event_type=etype, created_at=created_dt, repo_name=repo_name, actor_login=actor_login, payload=payload))
        return events
