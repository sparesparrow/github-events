"""
GitHub Events Monitor - Services Layer

Service layer components that match the architecture design:
- MetricsService: Aggregate counts, PR intervals, activity windows
- VisualizationService: Build images/figures (e.g., Plotly/PNG)
- EventsRepository: SQLite queries (read-only for API)
- HealthReporter: Health status reporting
"""

import asyncio
import io
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager

import aiosqlite
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt

from .dao import EventsDaoFactory

logger = logging.getLogger(__name__)


class EventsRepository:
    """Component: EventsRepository - SQLite queries (read-only for API)"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.dao_factory = EventsDaoFactory(db_path)
    
    async def _connect(self) -> aiosqlite.Connection:
        """Get database connection"""
        return await aiosqlite.connect(self.db_path)
    
    async def count_events_by_type(self, since_ts: datetime) -> Dict[str, int]:
        """Count events by type since the given timestamp"""
        daos = self.dao_factory.get_all_daos()
        counts = {}
        
        for event_type, dao in daos.items():
            counts[event_type] = await dao.count_total(since_ts)
        
        return counts
    
    async def pr_timestamps(self, repo: str) -> List[datetime]:
        """Get timestamps of PR 'opened' events for a repository"""
        pr_dao = self.dao_factory.get_pr_dao()
        return await pr_dao.get_pr_timestamps(repo)
    
    async def activity_by_repo(self, repo: str, since_ts: datetime) -> Dict[str, Any]:
        """Get activity breakdown for a repository since the given timestamp"""
        daos = self.dao_factory.get_all_daos()
        activity = {}
        total_events = 0
        
        for event_type, dao in daos.items():
            count = await dao.count_by_repo(repo, since_ts)
            activity[event_type] = {"count": count}
            total_events += count
        
        return {
            "activity": activity,
            "total_events": total_events
        }
    
    async def trending_since(self, since_ts: datetime, limit: int) -> List[Dict[str, Any]]:
        """Get trending repositories since the given timestamp"""
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                SELECT 
                    repo_name,
                    COUNT(*) as total_events,
                    SUM(CASE WHEN event_type = 'WatchEvent' THEN 1 ELSE 0 END) as watch_events,
                    SUM(CASE WHEN event_type = 'PullRequestEvent' THEN 1 ELSE 0 END) as pr_events,
                    SUM(CASE WHEN event_type = 'IssuesEvent' THEN 1 ELSE 0 END) as issue_events,
                    MIN(created_at) as first_event,
                    MAX(created_at) as last_event
                FROM events
                WHERE created_at >= ?
                GROUP BY repo_name
                ORDER BY total_events DESC
                LIMIT ?
                """,
                (since_ts, limit),
            )
            rows = await cursor.fetchall()
            
            repositories = []
            for row in rows:
                repo_name, total_events, watch_events, pr_events, issue_events, first_event, last_event = row
                repositories.append({
                    "repo_name": repo_name,
                    "total_events": total_events,
                    "watch_events": watch_events,
                    "pr_events": pr_events,
                    "issue_events": issue_events,
                    "first_event": first_event,
                    "last_event": last_event
                })
            
            return repositories
        finally:
            await db.close()
    
    async def get_pr_interval_stats(self, repo: str) -> Optional[Dict[str, Any]]:
        """Get PR interval statistics for a repository"""
        pr_dao = self.dao_factory.get_pr_dao()
        return await pr_dao.get_pr_interval_stats(repo)
    
    async def get_star_count_by_repo(self, repo: str, since_ts: datetime) -> int:
        """Get star count for a repository"""
        watch_dao = self.dao_factory.get_watch_dao()
        return await watch_dao.get_star_count_by_repo(repo, since_ts)
    
    async def get_issue_activity_summary(self, repo: str, since_ts: datetime) -> Dict[str, Any]:
        """Get issue activity summary for a repository"""
        issues_dao = self.dao_factory.get_issues_dao()
        return await issues_dao.get_issue_activity_summary(repo, since_ts)


class MetricsService:
    """Component: MetricsService - Aggregate counts, PR intervals, activity windows"""
    
    def __init__(self, repository: EventsRepository):
        self.repository = repository
    
    def _now(self) -> datetime:
        """Get current UTC time"""
        return datetime.now(timezone.utc)
    
    async def get_event_counts(self, offset_minutes: int) -> Dict[str, Any]:
        """Get event counts by type for the given time offset"""
        if offset_minutes <= 0:
            raise ValueError("offset_minutes must be positive")
        
        since_ts = self._now() - timedelta(minutes=offset_minutes)
        counts = await self.repository.count_events_by_type(since_ts)
        
        total_events = sum(counts.values())
        
        return {
            "offset_minutes": offset_minutes,
            "total_events": total_events,
            "counts": counts,
            "timestamp": self._now().isoformat()
        }
    
    async def get_pr_interval(self, repo: str) -> Optional[float]:
        """Calculate average time between pull requests for a repository"""
        result = await self.repository.get_pr_interval_stats(repo)
        return result
    
    async def get_repository_activity(self, repo: str, hours: int) -> Dict[str, Any]:
        """Get detailed activity summary for a specific repository"""
        since_ts = self._now() - timedelta(hours=hours)
        activity_data = await self.repository.activity_by_repo(repo, since_ts)
        
        return {
            "repo_name": repo,
            "hours": hours,
            "total_events": activity_data["total_events"],
            "activity": activity_data["activity"],
            "timestamp": self._now().isoformat()
        }
    
    async def get_trending(self, hours: int, limit: int) -> List[Dict[str, Any]]:
        """Get most active repositories by event count"""
        since_ts = self._now() - timedelta(hours=hours)
        repositories = await self.repository.trending_since(since_ts, limit)
        
        return repositories


class VisualizationService:
    """Component: VisualizationService - Build images/figures (e.g., Plotly/PNG)"""
    
    def __init__(self, repository: EventsRepository):
        self.repository = repository
    
    def _build_plot(self, data: Any) -> plt.Figure:
        """Build a matplotlib figure from data"""
        # This is a placeholder - actual implementation would be specific to each chart type
        fig, ax = plt.subplots()
        return fig
    
    async def trending_chart(self, hours: int, limit: int, format: str = "png") -> bytes:
        """Generate trending repositories chart"""
        from datetime import timedelta
        since_ts = datetime.now(timezone.utc) - timedelta(hours=hours)
        trending_data = await self.repository.trending_since(since_ts, limit)
        
        if not trending_data:
            raise ValueError("No data found for the specified time period")
        
        # Extract data for plotting
        repo_names = [repo['repo_name'].split('/')[-1][:20] for repo in trending_data]
        event_counts = [repo['total_events'] for repo in trending_data]
        
        # Create the chart
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        bars = ax.barh(range(len(repo_names)), event_counts, color='steelblue', alpha=0.7)
        
        # Customize the chart
        ax.set_yticks(range(len(repo_names)))
        ax.set_yticklabels(repo_names)
        ax.set_xlabel('Event Count')
        ax.set_title(f'Top {len(repo_names)} Repositories (Last {hours} Hours)')
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels on bars
        for i, (bar, count) in enumerate(zip(bars, event_counts)):
            width = bar.get_width()
            ax.text(width + max(event_counts) * 0.01, bar.get_y() + bar.get_height()/2, 
                   str(count), ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        
        # Convert to image
        img_buffer = io.BytesIO()
        if format == "svg":
            plt.savefig(img_buffer, format='svg', bbox_inches='tight', dpi=150)
        else:
            plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
        
        plt.close()
        img_buffer.seek(0)
        return img_buffer.read()
    
    async def pr_timeline(self, repo: str, format: str = "png") -> bytes:
        """Generate PR timeline chart"""
        # Get PR timeline data (this would need to be implemented in repository)
        # For now, we'll use a placeholder
        timestamps = await self.repository.pr_timestamps(repo)
        
        if len(timestamps) < 1:
            raise ValueError("No PR data found for the specified repository")
        
        # Create timeline chart
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Simple timeline - in practice you'd want to group by day
        dates = [ts.date() for ts in timestamps]
        counts = [1] * len(dates)  # Each PR counts as 1
        
        ax.plot(dates, counts, marker='o', color='steelblue', linewidth=2)
        ax.fill_between(dates, counts, color='steelblue', alpha=0.15)
        ax.set_xlabel('Date')
        ax.set_ylabel('PRs opened')
        ax.set_title(f"PR openings for {repo}")
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Convert to image
        img_buffer = io.BytesIO()
        if format == "svg":
            plt.savefig(img_buffer, format='svg', bbox_inches='tight', dpi=150)
        else:
            plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
        
        plt.close()
        img_buffer.seek(0)
        return img_buffer.read()


class HealthReporter:
    """Component: HealthReporter - Health status reporting"""
    
    def __init__(self, repository: EventsRepository):
        self.repository = repository
    
    async def status(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            # Test database connectivity
            db = await self.repository._connect()
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM events")
                row = await cursor.fetchone()
                event_count = row[0] if row else 0
            finally:
                await db.close()
            
            return {
                "status": "healthy",
                "database_connected": True,
                "total_events": event_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "database_connected": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
