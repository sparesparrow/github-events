from __future__ import annotations
import os
from typing import List, Optional

from src.github_events_monitor.infrastructure.api_request_reader import ApiRequestReader
from src.github_events_monitor.infrastructure.api_response_writer import ApiResponseWriter
from src.github_events_monitor.domain.events import GitHubEvent


class GitHubEventsCommandService:
    """
    Ingestion orchestration: fetch from GitHub and persist.
    """
    def __init__(self, reader: ApiRequestReader, writer: ApiResponseWriter) -> None:
        self.reader = reader
        self.writer = writer

    async def collect_now(self, limit: int = 100, target_repositories: Optional[List[str]] = None) -> int:
        repos = target_repositories
        if repos is None:
            env_val = os.getenv("TARGET_REPOSITORIES", "").strip()
            if env_val:
                repos = [r.strip() for r in env_val.split(",") if r.strip()]
        collected = 0
        if repos:
            for repo in repos:
                events = await self.reader.fetch_repo_events(repo=repo, limit=limit)
                collected += await self.writer.store_events(events)
        else:
            events = await self.reader.fetch_global_events(limit=limit)
            collected += await self.writer.store_events(events)
        return collected
