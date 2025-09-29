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

    # ------------------------------
    # Extended monitoring use-cases
    # ------------------------------

    async def get_stars(self, hours: int, repo: Optional[str] = None) -> Dict[str, Any]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=max(hours, 0))).timestamp())
        count = await self.repository.stars_since(since_ts=since_ts, repo=repo)
        return {"hours": hours, "repo": repo, "stars": count}

    async def get_releases(self, hours: int, repo: Optional[str] = None) -> Dict[str, Any]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=max(hours, 0))).timestamp())
        count = await self.repository.releases_since(since_ts=since_ts, repo=repo)
        return {"hours": hours, "repo": repo, "releases": count}

    async def get_push_activity(self, hours: int, repo: Optional[str] = None) -> Dict[str, Any]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=max(hours, 0))).timestamp())
        stats = await self.repository.push_activity_since(since_ts=since_ts, repo=repo)
        return {"hours": hours, "repo": repo, **stats}

    async def get_pr_merge_time(self, repo: str, hours: int) -> Dict[str, Any]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=max(hours, 0))).timestamp())
        durations = await self.repository.pr_merge_time_seconds(repo=repo, since_ts=since_ts)
        if not durations:
            return {"repo": repo, "hours": hours, "count": 0, "avg_seconds": None}
        avg = sum(durations) / len(durations)
        return {"repo": repo, "hours": hours, "count": len(durations), "avg_seconds": avg, "p50": _percentile(durations, 50), "p90": _percentile(durations, 90)}

    async def get_issue_first_response(self, repo: str, hours: int) -> Dict[str, Any]:
        since_ts = int((datetime.now(tz=timezone.utc) - timedelta(hours=max(hours, 0))).timestamp())
        durations = await self.repository.issue_first_response_seconds(repo=repo, since_ts=since_ts)
        if not durations:
            return {"repo": repo, "hours": hours, "count": 0, "avg_seconds": None}
        avg = sum(durations) / len(durations)
        return {"repo": repo, "hours": hours, "count": len(durations), "avg_seconds": avg, "p50": _percentile(durations, 50), "p90": _percentile(durations, 90)}


def _percentile(values: List[int], p: int) -> float:
    if not values:
        return float("nan")
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(values_sorted[int(k)])
    d0 = values_sorted[int(f)] * (c - k)
    d1 = values_sorted[int(c)] * (k - f)
    return float(d0 + d1)
