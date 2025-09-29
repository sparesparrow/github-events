from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional

from src.github_events_monitor.application.github_events_query_service import GitHubEventsQueryService
from src.github_events_monitor.application.github_events_command_service import GitHubEventsCommandService

router = APIRouter()


def get_query_service() -> GitHubEventsQueryService:
    # This function will be overridden in app wiring to inject the singleton
    raise HTTPException(status_code=500, detail="Query service not wired")


def get_command_service() -> GitHubEventsCommandService:
    raise HTTPException(status_code=500, detail="Command service not wired")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/metrics/event-counts")
async def metrics_event_counts(
    offset_minutes: Optional[int] = Query(None),
    offset_minutes_camel: Optional[int] = Query(None, alias="offsetMinutes"),
    repo: Optional[str] = None,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    final_offset = offset_minutes_camel or offset_minutes or 60
    return await svc.get_event_counts(offset_minutes=final_offset, repo=repo)


@router.get("/metrics/avg-pr-interval")
async def metrics_avg_pr_interval(
    repo: str,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return await svc.get_avg_pr_interval(repo=repo)


@router.get("/metrics/repository-activity")
async def metrics_repository_activity(
    repo: str,
    hours: int = 24,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return await svc.get_repository_activity(repo=repo, hours=hours)


@router.get("/metrics/trending")
async def metrics_trending(
    hours: int = 24,
    limit: int = 10,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return {"items": await svc.get_trending(hours=hours, limit=limit)}


@router.get("/metrics/event-counts-timeseries")
async def metrics_event_counts_timeseries(
    hours: int = 6,
    bucket_minutes: int = 5,
    repo: Optional[str] = None,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return {"series": await svc.get_event_counts_timeseries(hours=hours, bucket_minutes=bucket_minutes, repo=repo)}


@router.post("/collect")
async def collect_now(
    limit: int = 100,
    svc: GitHubEventsCommandService = Depends(get_command_service),
) -> dict:
    inserted = await svc.collect_now(limit=limit)
    return {"inserted": inserted}


# ------------------------------
# Extended monitoring endpoints
# ------------------------------

@router.get("/metrics/stars")
async def metrics_stars(
    hours: int = 24,
    repo: Optional[str] = None,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return await svc.get_stars(hours=hours, repo=repo)


@router.get("/metrics/releases")
async def metrics_releases(
    hours: int = 24,
    repo: Optional[str] = None,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return await svc.get_releases(hours=hours, repo=repo)


@router.get("/metrics/push-activity")
async def metrics_push_activity(
    hours: int = 24,
    repo: Optional[str] = None,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return await svc.get_push_activity(hours=hours, repo=repo)


@router.get("/metrics/pr-merge-time")
async def metrics_pr_merge_time(
    repo: str,
    hours: int = 168,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return await svc.get_pr_merge_time(repo=repo, hours=hours)


@router.get("/metrics/issue-first-response")
async def metrics_issue_first_response(
    repo: str,
    hours: int = 168,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    return await svc.get_issue_first_response(repo=repo, hours=hours)
