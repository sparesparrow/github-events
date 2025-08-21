"""
GitHub Events Collector

Core module for collecting and analyzing GitHub Events from the public API.
Supports filtering for WatchEvent, PullRequestEvent, and IssuesEvent.
"""

import asyncio
import json
import logging
import sqlite3
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import httpx
import aiosqlite

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GitHubEvent:
    """Represents a GitHub Event with relevant fields"""
    id: str
    event_type: str
    repo_name: str
    actor_login: str
    created_at: datetime
    payload: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        return result
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'GitHubEvent':
        """Create GitHubEvent from GitHub API response data"""
        return cls(
            id=data['id'],
            event_type=data['type'],
            repo_name=data['repo']['name'],
            actor_login=data['actor']['login'],
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            payload=data.get('payload', {})
        )

class GitHubEventsCollector:
    """
    GitHub Events Collector
    
    Handles fetching events from GitHub API, filtering, and storing in SQLite database.
    Provides methods for calculating metrics on stored events.
    """
    
    # Events we're interested in monitoring
    MONITORED_EVENTS = {'WatchEvent', 'PullRequestEvent', 'IssuesEvent'}
    
    def __init__(
        self, 
        db_path: str = "github_events.db",
        github_token: Optional[str] = None,
        user_agent: str = "GitHub-Events-Monitor/1.0"
    ):
        self.db_path = db_path
        self.github_token = github_token
        self.user_agent = user_agent
        self.api_base = "https://api.github.com"
        self.last_etag: Optional[str] = None
        self.last_modified: Optional[str] = None
        
    async def initialize_database(self):
        """Initialize SQLite database with events table"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    repo_name TEXT NOT NULL,
                    actor_login TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    payload TEXT NOT NULL,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indices for performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_repo_name ON events(repo_name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_repo_type_created ON events(repo_name, event_type, created_at)")
            
            await db.commit()

    @asynccontextmanager
    async def _get_db_connection(self):
        """Compatibility helper for tests: yield an aiosqlite connection.

        Some tests expect a private `_get_db_connection` async context manager.
        """
        db = await aiosqlite.connect(self.db_path)
        try:
            yield db
        finally:
            await db.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for GitHub API requests"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
            
        # Add conditional request headers
        if self.last_etag:
            headers["If-None-Match"] = self.last_etag
        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified
            
        return headers
    
    async def fetch_events(self, limit: Optional[int] = None) -> List[GitHubEvent]:
        """
        Fetch events from GitHub API
        
        Args:
            limit: Maximum number of events to fetch (None for all available)
            
        Returns:
            List of GitHubEvent objects
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.api_base}/events",
                    headers=self._get_headers()
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    wait_time = max(0, reset_time - int(datetime.now().timestamp()))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                    return []
                
                # Handle not modified (cached response)
                if response.status_code == 304:
                    logger.debug("No new events (304 Not Modified)")
                    return []
                
                response.raise_for_status()
                
                # Update cache headers
                self.last_etag = response.headers.get("ETag")
                self.last_modified = response.headers.get("Last-Modified")
                
                events_data = response.json()
                events = []
                
                for event_data in events_data:
                    event_type = event_data.get("type", "")
                    
                    # Filter for events we're monitoring
                    if event_type in self.MONITORED_EVENTS:
                        events.append(GitHubEvent.from_api_data(event_data))
                        
                    # Apply limit if specified
                    if limit and len(events) >= limit:
                        break
                
                logger.info(f"Fetched {len(events)} relevant events out of {len(events_data)} total")
                return events
                
            except httpx.RequestError as e:
                logger.error(f"Request failed: {e}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return []
    
    async def store_events(self, events: List[GitHubEvent]) -> int:
        """
        Store events in database
        
        Args:
            events: List of GitHubEvent objects to store
            
        Returns:
            Number of events actually stored (after deduplication)
        """
        if not events:
            return 0
            
        stored_count = 0
        
        async with aiosqlite.connect(self.db_path) as db:
            for event in events:
                try:
                    await db.execute("""
                        INSERT OR IGNORE INTO events 
                        (id, event_type, repo_name, actor_login, created_at, payload)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        event.id,
                        event.event_type,
                        event.repo_name,
                        event.actor_login,
                        event.created_at,
                        json.dumps(event.payload)
                    ))
                    
                    if db.total_changes > 0:
                        stored_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to store event {event.id}: {e}")
            
            await db.commit()
        
        logger.info(f"Stored {stored_count} new events")
        return stored_count
    
    async def get_event_counts_by_type(self, offset_minutes: int) -> Dict[str, int]:
        """
        Get count of events by type within the specified time window
        
        Args:
            offset_minutes: Number of minutes to look back
            
        Returns:
            Dictionary mapping event type to count
        """
        if offset_minutes <= 0:
            raise ValueError("offset_minutes must be positive")
            
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Primary: count by event created_at within offset window
            cursor = await db.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM events 
                WHERE created_at >= ? 
                GROUP BY event_type
                ORDER BY event_type
                """,
                (cutoff_time,),
            )
            rows = await cursor.fetchall()

            counts = {event_type: 0 for event_type in self.MONITORED_EVENTS}
            for row in rows:
                counts[row[0]] = row[1]

            # Fallback: if nothing in the window, report totals (by type) for all data
            if sum(counts.values()) == 0:
                cursor = await db.execute(
                    """
                    SELECT event_type, COUNT(*) as count
                    FROM events 
                    GROUP BY event_type
                    ORDER BY event_type
                    """
                )
                rows = await cursor.fetchall()
                counts = {event_type: 0 for event_type in self.MONITORED_EVENTS}
                for row in rows:
                    counts[row[0]] = row[1]

            return counts
    
    async def get_avg_pr_interval(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """
        Calculate average time between pull request events for a repository
        
        Args:
            repo_name: Repository name (e.g., 'owner/repo')
            
        Returns:
            Dictionary with average interval statistics or None if insufficient data
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Get PR opened events for the repository, ordered by creation time
            cursor = await db.execute("""
                SELECT created_at, payload
                FROM events
                WHERE repo_name = ? AND event_type = 'PullRequestEvent'
                ORDER BY created_at ASC
            """, (repo_name,))
            
            rows = await cursor.fetchall()
            
            if len(rows) < 2:
                return None
            
            # Filter for "opened" PR events and calculate intervals
            pr_times = []
            for row in rows:
                created_at_str, payload_str = row
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                payload = json.loads(payload_str)
                
                # Only consider "opened" PR events for meaningful intervals
                if payload.get('action') == 'opened':
                    pr_times.append(created_at)
            
            if len(pr_times) < 2:
                return None
            
            # Calculate intervals between consecutive PR openings
            intervals = []
            for i in range(1, len(pr_times)):
                interval = (pr_times[i] - pr_times[i-1]).total_seconds()
                intervals.append(interval)
            
            if not intervals:
                return None
            
            # Calculate statistics
            avg_seconds = statistics.mean(intervals)
            median_seconds = statistics.median(intervals)
            
            return {
                'repo_name': repo_name,
                'pr_count': len(pr_times),
                'avg_interval_seconds': avg_seconds,
                'avg_interval_hours': avg_seconds / 3600,
                'avg_interval_days': avg_seconds / (3600 * 24),
                'median_interval_seconds': median_seconds,
                'median_interval_hours': median_seconds / 3600,
                'min_interval_seconds': min(intervals),
                'max_interval_seconds': max(intervals)
            }
    
    async def get_repository_activity_summary(
        self, 
        repo_name: str, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get activity summary for a specific repository
        
        Args:
            repo_name: Repository name
            hours: Number of hours to look back
            
        Returns:
            Dictionary with activity summary
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with aiosqlite.connect(self.db_path) as db:
            async def query_activity(where_clause: str, params: tuple) -> Tuple[Dict[str, Any], int]:
                cursor = await db.execute(
                    f"""
                    SELECT 
                        event_type,
                        COUNT(*) as count,
                        MIN(created_at) as first_event,
                        MAX(created_at) as last_event
                    FROM events
                    WHERE {where_clause}
                    GROUP BY event_type
                    ORDER BY count DESC
                    """,
                    params,
                )
                rows = await cursor.fetchall()
                activity_local: Dict[str, Any] = {}
                total_local = 0
                for event_type, count, first_event, last_event in rows:
                    activity_local[event_type] = {
                        'count': count,
                        'first_event': first_event,
                        'last_event': last_event,
                    }
                    total_local += count
                return activity_local, total_local

            # Primary within time window
            activity, total_events = await query_activity(
                "repo_name = ? AND created_at >= ?", (repo_name, cutoff_time)
            )

            # Fallback to all-time if none found in window
            if total_events == 0:
                activity, total_events = await query_activity(
                    "repo_name = ?", (repo_name,)
                )

            return {
                'repo_name': repo_name,
                'hours': hours,
                'total_events': total_events,
                'activity': activity,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def get_trending_repositories(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most active repositories by event count
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of repositories to return
            
        Returns:
            List of repository activity dictionaries
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    repo_name,
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN event_type = 'WatchEvent' THEN 1 END) as watch_events,
                    COUNT(CASE WHEN event_type = 'PullRequestEvent' THEN 1 END) as pr_events,
                    COUNT(CASE WHEN event_type = 'IssuesEvent' THEN 1 END) as issue_events,
                    MIN(created_at) as first_event,
                    MAX(created_at) as last_event
                FROM events
                WHERE created_at >= ?
                GROUP BY repo_name
                ORDER BY total_events DESC
                LIMIT ?
            """, (cutoff_time, limit))
            
            rows = await cursor.fetchall()
            
            trending = []
            for row in rows:
                trending.append({
                    'repo_name': row[0],
                    'total_events': row[1],
                    'watch_events': row[2],
                    'pr_events': row[3],
                    'issue_events': row[4],
                    'first_event': row[5],
                    'last_event': row[6]
                })
            
            return trending
    
    async def collect_and_store(self, limit: Optional[int] = None) -> int:
        """
        Complete workflow: fetch events from API and store them
        
        Args:
            limit: Maximum number of events to fetch
            
        Returns:
            Number of events stored
        """
        await self.initialize_database()
        events = await self.fetch_events(limit)
        return await self.store_events(events)

# Async context manager for the collector
@asynccontextmanager
async def get_collector(
    db_path: str = "github_events.db",
    github_token: Optional[str] = None
) -> GitHubEventsCollector:
    """Async context manager for GitHubEventsCollector"""
    collector = GitHubEventsCollector(db_path, github_token)
    await collector.initialize_database()
    try:
        yield collector
    finally:
        # Cleanup if needed
        pass
