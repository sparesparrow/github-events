
"""
GitHub Events MCP Server

A Model Context Protocol (MCP) server that monitors GitHub Events API for specific event types
(WatchEvent, PullRequestEvent, IssuesEvent) and provides metrics through MCP tools and resources.

This implementation follows MCP best practices with proper prompts, tools, and resources.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import httpx
import asyncpg
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/github_events")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# GitHub API configuration
GITHUB_API_BASE = "https://api.github.com"
USER_AGENT = "GitHub-Events-MCP-Server/1.0"
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))  # seconds

class GitHubEvent(BaseModel):
    """GitHub Event model"""
    gh_id: str
    repo_name: str
    event_type: str
    created_at: datetime
    payload: Dict[str, Any]

class GitHubEventsPoller:
    """Handles GitHub Events API polling with rate limiting and caching"""

    def __init__(self, github_token: str):
        self.github_token = github_token
        self.last_etag: Optional[str] = None
        self.last_modified: Optional[str] = None
        self.session: Optional[httpx.AsyncClient] = None

    async def start(self):
        """Initialize HTTP session"""
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

    async def stop(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()

    async def fetch_events(self) -> List[GitHubEvent]:
        """Fetch events from GitHub API with conditional requests"""
        if not self.session:
            raise RuntimeError("Poller not started")

        headers = {}
        if self.last_etag:
            headers["If-None-Match"] = self.last_etag
        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified

        try:
            response = await self.session.get(
                f"{GITHUB_API_BASE}/events",
                headers=headers
            )

            # Handle rate limiting
            if response.status_code == 429:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                wait_time = max(0, reset_time - int(datetime.now().timestamp()))
                logger.warning(f"Rate limited. Waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
                return []

            # Handle not modified
            if response.status_code == 304:
                logger.debug("No new events (304 Not Modified)")
                return []

            response.raise_for_status()

            # Update cache headers
            self.last_etag = response.headers.get("ETag")
            self.last_modified = response.headers.get("Last-Modified")

            events_data = response.json()
            events = []

            # Filter for the events we're interested in
            interested_types = {"WatchEvent", "PullRequestEvent", "IssuesEvent"}

            for event_data in events_data:
                event_type = event_data.get("type", "")
                if event_type in interested_types:
                    events.append(GitHubEvent(
                        gh_id=event_data["id"],
                        repo_name=event_data["repo"]["name"],
                        event_type=event_type,
                        created_at=datetime.fromisoformat(event_data["created_at"].replace("Z", "+00:00")),
                        payload=event_data.get("payload", {})
                    ))

            logger.info(f"Fetched {len(events)} relevant events")
            return events

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

class DatabaseManager:
    """Handles database operations for storing events and computing metrics"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def start(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(self.database_url)
        await self.create_tables()

    async def stop(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        """Create necessary database tables"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id BIGSERIAL PRIMARY KEY,
                    gh_id TEXT UNIQUE NOT NULL,
                    repo_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    payload JSONB
                );

                CREATE INDEX IF NOT EXISTS idx_repo_created_at 
                ON events (repo_name, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_type_created_at 
                ON events (event_type, created_at DESC);

                -- Create aggregates table for performance
                CREATE TABLE IF NOT EXISTS event_aggregates (
                    repo_name TEXT,
                    event_type TEXT,
                    minute TIMESTAMPTZ,
                    count INTEGER,
                    PRIMARY KEY (repo_name, event_type, minute)
                );
            """)

    async def store_events(self, events: List[GitHubEvent]):
        """Store events in database with deduplication"""
        if not events:
            return

        async with self.pool.acquire() as conn:
            for event in events:
                try:
                    await conn.execute("""
                        INSERT INTO events (gh_id, repo_name, event_type, created_at, payload)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (gh_id) DO NOTHING
                    """, event.gh_id, event.repo_name, event.event_type, 
                    event.created_at, json.dumps(event.payload))
                except Exception as e:
                    logger.error(f"Error storing event {event.gh_id}: {e}")

    async def get_avg_pr_interval(self, repo: str) -> Optional[Dict[str, Any]]:
        """Calculate average time between PR events for a repository"""
        async with self.pool.acquire() as conn:
            result = await conn.fetch("""
                WITH pr_events AS (
                    SELECT created_at, repo_name,
                           LAG(created_at) OVER (ORDER BY created_at) as prev_created_at
                    FROM events 
                    WHERE repo_name = $1 AND event_type = 'PullRequestEvent'
                      AND payload->>'action' = 'opened'
                    ORDER BY created_at
                ),
                intervals AS (
                    SELECT EXTRACT(EPOCH FROM (created_at - prev_created_at)) as interval_seconds
                    FROM pr_events 
                    WHERE prev_created_at IS NOT NULL
                )
                SELECT 
                    COUNT(*) as pr_count,
                    AVG(interval_seconds) as avg_interval_seconds,
                    STDDEV(interval_seconds) as stddev_interval_seconds
                FROM intervals;
            """, repo)

            if result and result[0]["pr_count"]:
                row = result[0]
                return {
                    "repo": repo,
                    "pr_count": int(row["pr_count"]) + 1,  # +1 for the first PR
                    "avg_interval_seconds": float(row["avg_interval_seconds"]) if row["avg_interval_seconds"] else None,
                    "stddev_interval_seconds": float(row["stddev_interval_seconds"]) if row["stddev_interval_seconds"] else None
                }
            return {"repo": repo, "pr_count": 0, "avg_interval_seconds": None}

    async def get_event_counts(self, offset_minutes: int) -> Dict[str, int]:
        """Get event counts by type for the last N minutes"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)

        async with self.pool.acquire() as conn:
            result = await conn.fetch("""
                SELECT event_type, COUNT(*) as count
                FROM events 
                WHERE created_at >= $1
                GROUP BY event_type
                ORDER BY event_type;
            """, cutoff_time)

            return {row["event_type"]: int(row["count"]) for row in result}

# Global instances
poller = GitHubEventsPoller(GITHUB_TOKEN)
db_manager = DatabaseManager(DATABASE_URL)

# MCP Server setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting GitHub Events MCP Server...")

    # Start services
    await poller.start()
    await db_manager.start()

    # Start background polling task
    polling_task = asyncio.create_task(background_poller())

    yield

    # Stop services
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

    await poller.stop()
    await db_manager.stop()

    logger.info("GitHub Events MCP Server stopped.")

# Initialize MCP server
mcp = FastMCP(
    name="GitHub Events Monitor",
    dependencies=["httpx", "asyncpg", "matplotlib"],
    lifespan=lifespan
)

# Background polling task
async def background_poller():
    """Background task to continuously poll GitHub Events API"""
    while True:
        try:
            events = await poller.fetch_events()
            if events:
                await db_manager.store_events(events)
                logger.info(f"Stored {len(events)} events")
        except Exception as e:
            logger.error(f"Polling error: {e}")

        await asyncio.sleep(POLL_INTERVAL)

# MCP Tools
@mcp.tool()
async def get_avg_pr_interval(repo: str) -> Dict[str, Any]:
    """
    Calculate the average time between pull request events for a given repository.

    Args:
        repo: Repository name in format 'owner/repo' (e.g., 'microsoft/vscode')

    Returns:
        Dictionary containing repo name, PR count, and average interval in seconds
    """
    try:
        result = await db_manager.get_avg_pr_interval(repo)
        if result and result["avg_interval_seconds"] is not None:
            # Convert to human-readable format
            avg_seconds = result["avg_interval_seconds"]
            avg_hours = avg_seconds / 3600
            avg_days = avg_hours / 24

            result["avg_interval_human"] = {
                "seconds": round(avg_seconds, 2),
                "minutes": round(avg_seconds / 60, 2),
                "hours": round(avg_hours, 2),
                "days": round(avg_days, 2)
            }
        return result or {"error": "Repository not found or no PR events"}
    except Exception as e:
        logger.error(f"Error calculating PR interval: {e}")
        return {"error": str(e)}

@mcp.tool()
async def get_event_counts(offset_minutes: int) -> Dict[str, Any]:
    """
    Get the total number of events grouped by event type for a given time offset.

    Args:
        offset_minutes: Number of minutes to look back (e.g., 10 for last 10 minutes)

    Returns:
        Dictionary containing offset and event counts by type
    """
    try:
        if offset_minutes <= 0:
            return {"error": "offset_minutes must be greater than 0"}

        counts = await db_manager.get_event_counts(offset_minutes)
        total_events = sum(counts.values())

        return {
            "offset_minutes": offset_minutes,
            "total_events": total_events,
            "counts": counts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting event counts: {e}")
        return {"error": str(e)}

@mcp.tool()
async def get_repository_activity(repo: str, hours: int = 24) -> Dict[str, Any]:
    """
    Get detailed activity information for a specific repository.

    Args:
        repo: Repository name in format 'owner/repo'
        hours: Number of hours to look back (default: 24)

    Returns:
        Detailed repository activity information
    """
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        async with db_manager.pool.acquire() as conn:
            result = await conn.fetch("""
                SELECT 
                    event_type,
                    COUNT(*) as count,
                    MIN(created_at) as first_event,
                    MAX(created_at) as last_event
                FROM events 
                WHERE repo_name = $1 AND created_at >= $2
                GROUP BY event_type
                ORDER BY count DESC;
            """, repo, cutoff_time)

            activity = {}
            total_events = 0

            for row in result:
                event_type = row["event_type"]
                count = int(row["count"])
                activity[event_type] = {
                    "count": count,
                    "first_event": row["first_event"].isoformat(),
                    "last_event": row["last_event"].isoformat()
                }
                total_events += count

            return {
                "repo": repo,
                "hours": hours,
                "total_events": total_events,
                "activity": activity,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except Exception as e:
        logger.error(f"Error getting repository activity: {e}")
        return {"error": str(e)}

# MCP Resources
@mcp.resource("github://events/status")
async def server_status() -> str:
    """Provides the current status of the GitHub Events monitoring server"""
    try:
        # Get total event counts
        async with db_manager.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT repo_name) as unique_repos,
                    MIN(created_at) as oldest_event,
                    MAX(created_at) as newest_event
                FROM events;
            """)

            event_type_counts = await conn.fetch("""
                SELECT event_type, COUNT(*) as count 
                FROM events 
                GROUP BY event_type 
                ORDER BY count DESC;
            """)

            status = {
                "status": "running",
                "total_events": int(result["total_events"]) if result["total_events"] else 0,
                "unique_repositories": int(result["unique_repos"]) if result["unique_repos"] else 0,
                "oldest_event": result["oldest_event"].isoformat() if result["oldest_event"] else None,
                "newest_event": result["newest_event"].isoformat() if result["newest_event"] else None,
                "event_type_distribution": {
                    row["event_type"]: int(row["count"]) for row in event_type_counts
                },
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "poll_interval_seconds": POLL_INTERVAL
            }

            return json.dumps(status, indent=2)

    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.resource("github://events/recent/{event_type}")
async def recent_events(event_type: str) -> str:
    """
    Get recent events of a specific type

    Args:
        event_type: The type of events to retrieve (WatchEvent, PullRequestEvent, IssuesEvent)
    """
    try:
        valid_types = {"WatchEvent", "PullRequestEvent", "IssuesEvent"}
        if event_type not in valid_types:
            return json.dumps({"error": f"Invalid event type. Must be one of: {valid_types}"})

        async with db_manager.pool.acquire() as conn:
            result = await conn.fetch("""
                SELECT repo_name, created_at, payload
                FROM events 
                WHERE event_type = $1
                ORDER BY created_at DESC 
                LIMIT 20;
            """, event_type)

            events = []
            for row in result:
                events.append({
                    "repo": row["repo_name"],
                    "created_at": row["created_at"].isoformat(),
                    "payload": row["payload"]
                })

            return json.dumps({
                "event_type": event_type,
                "count": len(events),
                "events": events
            }, indent=2)

    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        return json.dumps({"error": str(e)})

# MCP Prompts
@mcp.prompt()
async def analyze_repository_trends(repo: str) -> str:
    """
    Generate a comprehensive analysis prompt for repository activity trends.

    Args:
        repo: Repository name to analyze
    """
    try:
        # Get data for the prompt
        pr_data = await get_avg_pr_interval(repo)
        activity_data = await get_repository_activity(repo, 168)  # 1 week

        prompt = f"""
Analyze the GitHub activity trends for repository: {repo}

Current Repository Statistics:
- Pull Request Activity: {pr_data.get('pr_count', 0)} PRs tracked
- Average time between PRs: {pr_data.get('avg_interval_human', {}).get('hours', 'N/A')} hours
- Recent activity (7 days): {activity_data.get('total_events', 0)} total events

Event Distribution:
"""

        for event_type, data in activity_data.get('activity', {}).items():
            prompt += f"- {event_type}: {data['count']} events\n"

        prompt += """

Please provide insights on:
1. Repository health and activity patterns
2. Development velocity indicators
3. Community engagement level
4. Recommendations for improvement
5. Any notable trends or anomalies

Base your analysis on the GitHub event data provided above.
"""

        return prompt

    except Exception as e:
        return f"Error generating analysis prompt: {e}"

@mcp.prompt()
async def create_monitoring_alert(threshold_minutes: int = 60) -> str:
    """
    Create a monitoring alert configuration prompt.

    Args:
        threshold_minutes: Alert threshold in minutes
    """
    try:
        # Get current activity levels
        counts = await get_event_counts(threshold_minutes)

        prompt = f"""
Create a monitoring and alerting strategy for GitHub Events monitoring.

Current Activity Levels (last {threshold_minutes} minutes):
- Total Events: {counts.get('total_events', 0)}
- Event Breakdown: {counts.get('counts', {})}

Please design monitoring rules and alerts for:
1. **Activity Thresholds**: Define when activity is too low/high
2. **Event Type Anomalies**: Detect unusual patterns in event types  
3. **Repository Health**: Identify repos with concerning activity patterns
4. **System Health**: Monitor the MCP server performance

Include:
- Specific metrics to track
- Alert thresholds and conditions
- Escalation procedures
- Dashboard requirements
- Automation suggestions

Consider both technical monitoring and business impact analysis.
"""

        return prompt

    except Exception as e:
        return f"Error generating monitoring prompt: {e}"

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="stdio")
