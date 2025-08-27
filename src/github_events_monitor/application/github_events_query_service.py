from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import math

from src.github_events_monitor.infrastructure.events_repository import EventsRepository


class GitHubEventsQueryService:
    """
    Query side: metrics and aggregations.
    """
    def __init__(self, repository: EventsRepository) -> None:
        self.repository = repository

    async def get_event_counts(self, offset_minutes: int, repo: Optional[str] = None) -> Dict[str, int]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(minutes=max(offset_minutes, 0))).timestamp())
        return await self.repository.count_events_by_type(since_ts=since_ts, repo=repo)

    async def get_avg_pr_interval(self, repo: str) -> Dict[str, Any]:
        stamps = await self.repository.pr_timestamps(repo=repo)
        if len(stamps) < 2:
            return {"repo": repo, "count": len(stamps), "avg_seconds": None}
        diffs = [stamps[i] - stamps[i - 1] for i in range(1, len(stamps))]
        avg = sum(diffs) / len(diffs)
        return {"repo": repo, "count": len(stamps), "avg_seconds": avg, "avg_minutes": avg / 60.0, "avg_hours": avg / 3600.0}

    async def get_repository_activity(self, repo: str, hours: int) -> Dict[str, int]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=max(hours, 0))).timestamp())
        return await self.repository.activity_by_repo(repo=repo, since_ts=since_ts)

    async def get_trending(self, hours: int, limit: int = 10) -> List[Dict[str, Any]]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=max(hours, 0))).timestamp())
        return await self.repository.trending_since(since_ts=since_ts, limit=limit)

    async def get_event_counts_timeseries(self, hours: int, bucket_minutes: int, repo: Optional[str] = None) -> List[Dict[str, Any]]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=max(hours, 0))).timestamp())
        return await self.repository.event_counts_timeseries(since_ts=since_ts, bucket_minutes=bucket_minutes, repo=repo)
