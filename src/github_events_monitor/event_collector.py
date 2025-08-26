"""
GitHub Events Collector

Core module for collecting and analyzing GitHub Events from the public API.
Supports filtering for WatchEvent, PullRequestEvent, and IssuesEvent.
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, AsyncIterator, AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import aiosqlite
from .database import SchemaDao, EventsWriteDao, AggregatesDao, DatabaseManager
from .event import GitHubEvent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
		user_agent: str = "GitHub-Events-Monitor/1.0",
		target_repositories: Optional[List[str]] = None,
		db_manager: Optional[DatabaseManager] = None,
	):
		self.db_path = db_path
		self.github_token = github_token
		self.user_agent = user_agent
		self.api_base = "https://api.github.com"
		self.target_repositories = target_repositories
		self.last_etag: Optional[str] = None
		self.last_modified: Optional[str] = None
		# Optional DB manager
		self._dbm: Optional[DatabaseManager] = db_manager
		if self._dbm is None:
			self._dbm = DatabaseManager(db_path=self.db_path)
		
	async def initialize_database(self):
		"""Initialize SQLite database with events table"""
		await self._dbm.initialize()
	
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
				# Expose suggested poll interval if present
				suggested_poll = response.headers.get("X-Poll-Interval")
				if suggested_poll:
					try:
						self.suggested_poll_seconds = int(suggested_poll)
					except Exception:
						self.suggested_poll_seconds = None
				
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
	
	async def fetch_repository_events(self, repo_name: str, limit: Optional[int] = None) -> List[GitHubEvent]:
		"""
		Fetch events from a specific repository
		
		Args:
			repo_name: Repository name in format 'owner/repo'
			limit: Maximum number of events to fetch (None for all available)
			
		Returns:
			List of GitHubEvent objects
		"""
		async with httpx.AsyncClient(timeout=30.0) as client:
			try:
				response = await client.get(
					f"{self.api_base}/repos/{repo_name}/events",
					headers=self._get_headers()
				)
				
				# Handle rate limiting
				if response.status_code == 429:
					reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
					wait_time = max(0, reset_time - int(datetime.now().timestamp()))
					logger.warning(f"Rate limited for {repo_name}. Waiting {wait_time} seconds")
					await asyncio.sleep(wait_time)
					return []
				
				# Handle not found
				if response.status_code == 404:
					logger.warning(f"Repository {repo_name} not found or not accessible")
					return []
				
				response.raise_for_status()
				
				# Suggested poll interval for repo events
				suggested_poll = response.headers.get("X-Poll-Interval")
				if suggested_poll:
					try:
						self.suggested_poll_seconds = int(suggested_poll)
					except Exception:
						self.suggested_poll_seconds = None
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
				
				logger.info(f"Fetched {len(events)} relevant events from {repo_name} out of {len(events_data)} total")
				return events
				
			except httpx.RequestError as e:
				logger.error(f"Request failed for {repo_name}: {e}")
				return []
			except Exception as e:
				logger.error(f"Unexpected error for {repo_name}: {e}")
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
		
		write_dao = self._dbm.writes
		payloads = [
			{
				"id": event.id,
				"event_type": event.event_type,
				"repo_name": event.repo_name,
				"actor_login": event.actor_login,
				"created_at": event.created_at,
				"payload": event.payload,
			}
			for event in events
		]
		stored_count = await write_dao.insert_events(payloads)
		
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
		
		aggregates = self._dbm.aggregates
		counts = await aggregates.get_counts_by_type_since(cutoff_time)
		# Ensure all monitored keys are present
		counts = {**{event_type: 0 for event_type in self.MONITORED_EVENTS}, **counts}
		if sum(counts.values()) == 0:
			counts_total = await aggregates.get_counts_by_type_total()
			counts = {**{event_type: 0 for event_type in self.MONITORED_EVENTS}, **counts_total}
		return counts
	
	async def get_avg_pr_interval(self, repo_name: str) -> Optional[Dict[str, Any]]:
		"""
		Calculate average time between pull request events for a repository
		
		Args:
			repo_name: Repository name (e.g., 'owner/repo')
			
		Returns:
			Dictionary with average interval statistics or None if insufficient data
		"""
		pr_dao = self._dbm.events.get_pr_dao()
		return await pr_dao.get_pr_interval_stats(repo_name)
	
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
		
		aggregates = self._dbm.aggregates
		activity, total_events = await aggregates.get_repository_activity_summary(repo_name, cutoff_time)
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
		
		aggregates = self._dbm.aggregates
		return await aggregates.get_trending_since(cutoff_time, limit)
	
	async def get_event_counts_timeseries(self, hours: int = 24, bucket_minutes: int = 60) -> List[Dict[str, Any]]:
		"""
		Return a simple time-series of total events per bucket.

		Args:
			hours: Window to look back
			bucket_minutes: Size of each time bucket in minutes

		Returns:
			List of dicts: [{"bucket_start": iso, "total": n}] ordered by time.
		"""
		from datetime import timedelta
		if bucket_minutes <= 0:
			bucket_minutes = 60
		cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
		aggregates = self._dbm.aggregates
		return await aggregates.get_event_counts_timeseries(cutoff_time)
	
	async def get_pr_timeline(self, repo_name: str, days: int = 7) -> List[Dict[str, Any]]:
		"""
		Return per-day counts of 'opened' PullRequestEvent for a repository over the
		last N days. Returns a list of dicts: [{"date": "YYYY-MM-DD", "count": n}],
		including days with zero activity, ordered by date ascending.
		"""
		if days <= 0:
			days = 1
		pr_dao = self._dbm.events.get_pr_dao()
		series = await pr_dao.get_pr_timeline(repo_name, days)
		return series

	async def collect_and_store(self, limit: Optional[int] = None) -> int:
		"""Complete workflow: fetch events and persist them to the database."""
		await self.initialize_database()
		if self.target_repositories:
			all_events: List[GitHubEvent] = []
			for repo in self.target_repositories:
				repo_events = await self.fetch_repository_events(repo, limit)
				all_events.extend(repo_events)
				logger.info(f"Collected {len(repo_events)} events from {repo}")
			return await self.store_events(all_events)
		else:
			# Fall back to general public events
			events = await self.fetch_events(limit)
			return await self.store_events(events)

# Async context manager for the collector

@asynccontextmanager
async def get_collector(
	db_path: str = "github_events.db",
	github_token: Optional[str] = None
) -> AsyncGenerator["GitHubEventsCollector", None]:
	"""Async context manager for GitHubEventsCollector"""
	collector = GitHubEventsCollector(db_path, github_token)
	await collector.initialize_database()
	try:
		yield collector
	finally:
		# Cleanup if needed
		pass


