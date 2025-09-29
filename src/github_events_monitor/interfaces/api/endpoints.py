from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import datetime, timezone

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
# Extended monitoring endpoints (from main branch)
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


# Enhanced Monitoring Endpoints

@router.get("/metrics/repository-health")
async def metrics_repository_health(
    repo: str,
    hours: int = 168,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get comprehensive repository health score and metrics"""
    return await svc.get_repository_health_score(repo=repo, hours=hours)


@router.get("/metrics/developer-productivity")
async def metrics_developer_productivity(
    repo: str,
    hours: int = 168,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get developer productivity metrics for a repository"""
    result = await svc.get_developer_productivity_metrics(repo=repo, hours=hours)
    return {"repo": repo, "hours": hours, "developers": result}


@router.get("/metrics/security-monitoring")
async def metrics_security_monitoring(
    repo: str,
    hours: int = 168,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get security monitoring report for a repository"""
    return await svc.get_security_monitoring_report(repo=repo, hours=hours)


@router.get("/metrics/event-anomalies")
async def metrics_event_anomalies(
    repo: str,
    hours: int = 168,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Detect anomalies in event patterns for a repository"""
    anomalies = await svc.detect_event_anomalies(repo=repo, hours=hours)
    return {"repo": repo, "hours": hours, "anomalies": anomalies}


@router.get("/metrics/release-deployment")
async def metrics_release_deployment(
    repo: str,
    hours: int = 720,  # 30 days default
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get release and deployment metrics for a repository"""
    return await svc.get_release_deployment_metrics(repo=repo, hours=hours)


@router.get("/metrics/community-engagement")
async def metrics_community_engagement(
    repo: str,
    hours: int = 168,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get community engagement metrics for a repository"""
    return await svc.get_community_engagement_metrics(repo=repo, hours=hours)


@router.get("/metrics/event-types-summary")
async def metrics_event_types_summary(
    repo: Optional[str] = None,
    hours: int = 168,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get summary of all supported event types and their counts"""
    from src.github_events_monitor.event_collector import GitHubEventsCollector
    
    # Get event counts for all monitored events
    event_counts = await svc.get_event_counts(offset_minutes=hours * 60, repo=repo)
    
    # Add event type descriptions
    event_descriptions = {
        'WatchEvent': 'Repository stars/watching',
        'PullRequestEvent': 'Pull requests opened/closed/merged',
        'IssuesEvent': 'Issues opened/closed/labeled',
        'PushEvent': 'Code pushes to repositories',
        'ForkEvent': 'Repository forks',
        'CreateEvent': 'Branch/tag creation',
        'DeleteEvent': 'Branch/tag deletion',
        'ReleaseEvent': 'Releases published',
        'CommitCommentEvent': 'Comments on commits',
        'IssueCommentEvent': 'Comments on issues',
        'PullRequestReviewEvent': 'PR reviews',
        'PullRequestReviewCommentEvent': 'Comments on PR reviews',
        'PublicEvent': 'Repository made public',
        'MemberEvent': 'Collaborators added/removed',
        'TeamAddEvent': 'Teams added to repositories',
        'GollumEvent': 'Wiki pages created/updated',
        'DeploymentEvent': 'Deployments created',
        'DeploymentStatusEvent': 'Deployment status updates',
        'StatusEvent': 'Commit status updates',
        'CheckRunEvent': 'Check runs completed',
        'CheckSuiteEvent': 'Check suites completed',
        'SponsorshipEvent': 'Sponsorship changes',
        'MarketplacePurchaseEvent': 'Marketplace purchases'
    }
    
    # Enhance event counts with descriptions and categories
    enhanced_counts = {}
    for event_type in GitHubEventsCollector.MONITORED_EVENTS:
        count = event_counts.get('counts', {}).get(event_type, 0)
        enhanced_counts[event_type] = {
            'count': count,
            'description': event_descriptions.get(event_type, 'Unknown event type'),
            'category': _get_event_category(event_type)
        }
    
    return {
        'repo': repo,
        'hours': hours,
        'total_monitored_events': len(GitHubEventsCollector.MONITORED_EVENTS),
        'total_events': sum(ec['count'] for ec in enhanced_counts.values()),
        'event_types': enhanced_counts,
        'categories': _get_event_categories_summary(enhanced_counts),
        'timestamp': event_counts.get('timestamp')
    }


def _get_event_category(event_type: str) -> str:
    """Get category for an event type"""
    categories = {
        'WatchEvent': 'engagement',
        'PullRequestEvent': 'development',
        'IssuesEvent': 'development',
        'PushEvent': 'development',
        'ForkEvent': 'engagement',
        'CreateEvent': 'development',
        'DeleteEvent': 'development',
        'ReleaseEvent': 'deployment',
        'CommitCommentEvent': 'collaboration',
        'IssueCommentEvent': 'collaboration',
        'PullRequestReviewEvent': 'collaboration',
        'PullRequestReviewCommentEvent': 'collaboration',
        'PublicEvent': 'management',
        'MemberEvent': 'management',
        'TeamAddEvent': 'management',
        'GollumEvent': 'documentation',
        'DeploymentEvent': 'deployment',
        'DeploymentStatusEvent': 'deployment',
        'StatusEvent': 'quality',
        'CheckRunEvent': 'quality',
        'CheckSuiteEvent': 'quality',
        'SponsorshipEvent': 'engagement',
        'MarketplacePurchaseEvent': 'engagement'
    }
    return categories.get(event_type, 'other')


def _get_event_categories_summary(enhanced_counts: dict) -> dict:
    """Get summary by event categories"""
    categories = {}
    for event_type, data in enhanced_counts.items():
        category = data['category']
        if category not in categories:
            categories[category] = {'count': 0, 'event_types': []}
        categories[category]['count'] += data['count']
        if data['count'] > 0:  # Only include active event types
            categories[category]['event_types'].append(event_type)
    
    return categories


# Commit Monitoring Endpoints

@router.get("/commits/recent")
async def commits_recent(
    repo: str,
    hours: int = 24,
    limit: int = 50,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get recent commits for a repository with summaries"""
    commits = await svc.get_recent_commits(repo=repo, hours=hours, limit=limit)
    return {
        "repo": repo,
        "hours": hours,
        "limit": limit,
        "total_commits": len(commits),
        "commits": commits
    }


@router.get("/commits/summary")
async def commits_summary(
    repo: str,
    hours: int = 24,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get comprehensive change summary for a repository"""
    return await svc.get_repository_change_summary(repo=repo, hours=hours)


@router.get("/commits/{commit_sha}")
async def commits_detail(
    commit_sha: str,
    repo: str,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get detailed information about a specific commit"""
    return await svc.get_commit_details(commit_sha=commit_sha, repo=repo)


@router.get("/commits/{commit_sha}/files")
async def commits_files(
    commit_sha: str,
    repo: str,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get file changes for a specific commit"""
    files = await svc.get_commit_files(commit_sha=commit_sha, repo=repo)
    return {
        "commit_sha": commit_sha,
        "repo": repo,
        "files": files
    }


@router.get("/monitoring/commits")
async def monitoring_commits_multi_repo(
    repos: str,  # Comma-separated list of repositories
    hours: int = 24,
    limit_per_repo: int = 10,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Monitor recent commits across multiple repositories"""
    repo_list = [repo.strip() for repo in repos.split(',') if repo.strip()]
    
    results = {}
    total_commits = 0
    
    for repo in repo_list:
        try:
            commits = await svc.get_recent_commits(repo=repo, hours=hours, limit=limit_per_repo)
            results[repo] = {
                "commits": commits,
                "count": len(commits),
                "summary": await svc.get_repository_change_summary(repo=repo, hours=hours) if commits else None
            }
            total_commits += len(commits)
        except Exception as e:
            results[repo] = {
                "error": str(e),
                "commits": [],
                "count": 0,
                "summary": None
            }
    
    return {
        "repositories": repo_list,
        "hours": hours,
        "total_repositories": len(repo_list),
        "total_commits": total_commits,
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/monitoring/commits/categories")
async def monitoring_commits_by_category(
    repo: str,
    hours: int = 24,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get commits grouped by change categories"""
    return await svc.get_commits_by_category(repo=repo, hours=hours)


@router.get("/monitoring/commits/authors")
async def monitoring_commits_by_author(
    repo: str,
    hours: int = 168,  # 1 week default
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get commit statistics grouped by author"""
    return await svc.get_commits_by_author(repo=repo, hours=hours)


@router.get("/monitoring/commits/impact")
async def monitoring_high_impact_commits(
    repo: str,
    hours: int = 168,
    min_impact_score: float = 70.0,
    svc: GitHubEventsQueryService = Depends(get_query_service),
) -> dict:
    """Get high-impact commits for a repository"""
    commits = await svc.get_high_impact_commits(
        repo=repo, 
        hours=hours, 
        min_impact_score=min_impact_score
    )
    return {
        "repo": repo,
        "hours": hours,
        "min_impact_score": min_impact_score,
        "high_impact_commits": commits
    }