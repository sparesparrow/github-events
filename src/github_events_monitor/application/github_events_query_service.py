from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import math
from fastapi import HTTPException

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
    # Extended monitoring use-cases (from main branch)
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

    # Enhanced monitoring methods - delegate to collector for now
    async def get_repository_health_score(self, repo: str, hours: int = 168) -> Dict[str, Any]:
        """Get repository health score - delegates to collector for implementation"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        # Create collector instance to access enhanced monitoring methods
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_repository_health_score(repo, hours)

    async def get_developer_productivity_metrics(self, repo: str, hours: int = 168) -> List[Dict[str, Any]]:
        """Get developer productivity metrics"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_developer_productivity_metrics(repo, hours)

    async def get_security_monitoring_report(self, repo: str, hours: int = 168) -> Dict[str, Any]:
        """Get security monitoring report"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_security_monitoring_report(repo, hours)

    async def detect_event_anomalies(self, repo: str, hours: int = 168) -> List[Dict[str, Any]]:
        """Detect event anomalies"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.detect_event_anomalies(repo, hours)

    async def get_release_deployment_metrics(self, repo: str, hours: int = 720) -> Dict[str, Any]:
        """Get release and deployment metrics"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_release_deployment_metrics(repo, hours)

    async def get_community_engagement_metrics(self, repo: str, hours: int = 168) -> Dict[str, Any]:
        """Get community engagement metrics"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_community_engagement_metrics(repo, hours)

    # Commit monitoring methods
    async def get_recent_commits(self, repo: str, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent commits for a repository with summaries"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_recent_commits(repo, hours, limit)

    async def get_repository_change_summary(self, repo: str, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive change summary for a repository"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_repository_change_summary(repo, hours)

    async def get_commit_details(self, commit_sha: str, repo: str) -> Dict[str, Any]:
        """Get detailed information about a specific commit"""
        import aiosqlite
        import json
        
        async with aiosqlite.connect(self.repository.db_connection.db_path) as db:
            query = """
            SELECT 
                c.sha, c.author_name, c.author_login, c.message, c.commit_date,
                c.branch_name, c.stats_additions, c.stats_deletions, 
                c.stats_total_changes, c.files_changed, c.parent_shas,
                cs.short_summary, cs.detailed_summary, cs.change_categories,
                cs.impact_score, cs.risk_level, cs.breaking_changes,
                cs.security_relevant, cs.performance_impact, cs.complexity_score
            FROM commits c
            LEFT JOIN commit_summaries cs ON c.sha = cs.commit_sha
            WHERE c.sha = ? AND c.repo_name = ?
            """
            
            cursor = await db.execute(query, (commit_sha, repo))
            row = await cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Commit {commit_sha} not found in {repo}")
            
            return {
                'sha': row[0],
                'author_name': row[1],
                'author_login': row[2],
                'message': row[3],
                'commit_date': row[4],
                'branch_name': row[5],
                'stats': {
                    'additions': row[6],
                    'deletions': row[7],
                    'total_changes': row[8]
                },
                'files_changed': row[9],
                'parent_shas': json.loads(row[10]) if row[10] else [],
                'summary': {
                    'short': row[11],
                    'detailed': row[12],
                    'categories': json.loads(row[13]) if row[13] else [],
                    'impact_score': row[14],
                    'risk_level': row[15],
                    'breaking_changes': bool(row[16]),
                    'security_relevant': bool(row[17]),
                    'performance_impact': row[18],
                    'complexity_score': row[19]
                }
            }

    async def get_commit_files(self, commit_sha: str, repo: str) -> List[Dict[str, Any]]:
        """Get file changes for a specific commit"""
        import aiosqlite
        
        async with aiosqlite.connect(self.repository.db_connection.db_path) as db:
            query = """
            SELECT filename, status, additions, deletions, changes, previous_filename
            FROM commit_files
            WHERE commit_sha = ? AND repo_name = ?
            ORDER BY filename
            """
            
            cursor = await db.execute(query, (commit_sha, repo))
            rows = await cursor.fetchall()
            
            return [
                {
                    'filename': row[0],
                    'status': row[1],
                    'additions': row[2],
                    'deletions': row[3],
                    'changes': row[4],
                    'previous_filename': row[5]
                }
                for row in rows
            ]

    async def get_commits_by_category(self, repo: str, hours: int = 24) -> Dict[str, Any]:
        """Get commits grouped by change categories"""
        import aiosqlite
        import json
        from datetime import datetime, timedelta, timezone
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with aiosqlite.connect(self.repository.db_connection.db_path) as db:
            query = """
            SELECT cs.change_categories, c.sha, c.message, c.author_login, c.commit_date
            FROM commit_summaries cs
            JOIN commits c ON cs.commit_sha = c.sha
            WHERE c.repo_name = ? AND c.commit_date >= ?
            ORDER BY c.commit_date DESC
            """
            
            cursor = await db.execute(query, (repo, cutoff_time.isoformat()))
            rows = await cursor.fetchall()
            
            categories = {}
            for row in rows:
                try:
                    commit_categories = json.loads(row[0]) if row[0] else ['other']
                except json.JSONDecodeError:
                    commit_categories = ['other']
                
                commit_info = {
                    'sha': row[1],
                    'message': row[2],
                    'author_login': row[3],
                    'commit_date': row[4]
                }
                
                for category in commit_categories:
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(commit_info)
            
            return {
                'repo': repo,
                'hours': hours,
                'categories': categories,
                'total_commits': len(rows)
            }

    async def get_commits_by_author(self, repo: str, hours: int = 168) -> Dict[str, Any]:
        """Get commit statistics grouped by author"""
        import aiosqlite
        from datetime import datetime, timedelta, timezone
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with aiosqlite.connect(self.repository.db_connection.db_path) as db:
            query = """
            SELECT 
                c.author_login,
                c.author_name,
                COUNT(*) as commit_count,
                SUM(c.stats_additions) as total_additions,
                SUM(c.stats_deletions) as total_deletions,
                SUM(c.files_changed) as total_files_changed,
                AVG(cs.impact_score) as avg_impact_score,
                COUNT(CASE WHEN cs.breaking_changes = 1 THEN 1 END) as breaking_commits,
                COUNT(CASE WHEN cs.security_relevant = 1 THEN 1 END) as security_commits
            FROM commits c
            LEFT JOIN commit_summaries cs ON c.sha = cs.commit_sha
            WHERE c.repo_name = ? AND c.commit_date >= ?
            GROUP BY c.author_login, c.author_name
            ORDER BY commit_count DESC
            """
            
            cursor = await db.execute(query, (repo, cutoff_time.isoformat()))
            rows = await cursor.fetchall()
            
            authors = []
            for row in rows:
                authors.append({
                    'author_login': row[0],
                    'author_name': row[1],
                    'commit_count': row[2],
                    'total_additions': row[3] or 0,
                    'total_deletions': row[4] or 0,
                    'total_files_changed': row[5] or 0,
                    'avg_impact_score': round(row[6], 2) if row[6] else 0,
                    'breaking_commits': row[7] or 0,
                    'security_commits': row[8] or 0
                })
            
            return {
                'repo': repo,
                'hours': hours,
                'total_authors': len(authors),
                'authors': authors
            }

    async def get_high_impact_commits(self, repo: str, hours: int = 168, min_impact_score: float = 70.0) -> List[Dict[str, Any]]:
        """Get high-impact commits for a repository"""
        import aiosqlite
        import json
        from datetime import datetime, timedelta, timezone
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with aiosqlite.connect(self.repository.db_connection.db_path) as db:
            query = """
            SELECT 
                c.sha, c.author_name, c.author_login, c.message, c.commit_date,
                c.branch_name, c.stats_additions, c.stats_deletions, 
                c.stats_total_changes, c.files_changed,
                cs.short_summary, cs.detailed_summary, cs.change_categories,
                cs.impact_score, cs.risk_level, cs.breaking_changes,
                cs.security_relevant, cs.performance_impact
            FROM commits c
            JOIN commit_summaries cs ON c.sha = cs.commit_sha
            WHERE c.repo_name = ? AND c.commit_date >= ? AND cs.impact_score >= ?
            ORDER BY cs.impact_score DESC, c.commit_date DESC
            """
            
            cursor = await db.execute(query, (repo, cutoff_time.isoformat(), min_impact_score))
            rows = await cursor.fetchall()
            
            commits = []
            for row in rows:
                commits.append({
                    'sha': row[0],
                    'author_name': row[1],
                    'author_login': row[2],
                    'message': row[3],
                    'commit_date': row[4],
                    'branch_name': row[5],
                    'stats': {
                        'additions': row[6],
                        'deletions': row[7],
                        'total_changes': row[8]
                    },
                    'files_changed': row[9],
                    'summary': {
                        'short': row[10],
                        'detailed': row[11],
                        'categories': json.loads(row[12]) if row[12] else [],
                        'impact_score': row[13],
                        'risk_level': row[14],
                        'breaking_changes': bool(row[15]),
                        'security_relevant': bool(row[16]),
                        'performance_impact': row[17]
                    }
                })
            
            return commits

    # Enhanced monitoring methods - delegate to collector for now
    async def get_repository_health_score(self, repo: str, hours: int = 168) -> Dict[str, Any]:
        """Get repository health score - delegates to collector for implementation"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        # Create collector instance to access enhanced monitoring methods
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_repository_health_score(repo, hours)

    async def get_developer_productivity_metrics(self, repo: str, hours: int = 168) -> List[Dict[str, Any]]:
        """Get developer productivity metrics"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_developer_productivity_metrics(repo, hours)

    async def get_security_monitoring_report(self, repo: str, hours: int = 168) -> Dict[str, Any]:
        """Get security monitoring report"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_security_monitoring_report(repo, hours)

    async def detect_event_anomalies(self, repo: str, hours: int = 168) -> List[Dict[str, Any]]:
        """Detect event anomalies"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.detect_event_anomalies(repo, hours)

    async def get_release_deployment_metrics(self, repo: str, hours: int = 720) -> Dict[str, Any]:
        """Get release and deployment metrics"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_release_deployment_metrics(repo, hours)

    async def get_community_engagement_metrics(self, repo: str, hours: int = 168) -> Dict[str, Any]:
        """Get community engagement metrics"""
        from src.github_events_monitor.event_collector import GitHubEventsCollector
        from src.github_events_monitor.database import DatabaseManager
        
        db_manager = DatabaseManager(db_path=self.repository.db_connection.db_path)
        collector = GitHubEventsCollector(db_manager=db_manager)
        return await collector.get_community_engagement_metrics(repo, hours)


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