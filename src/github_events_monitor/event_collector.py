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
from typing import Dict, List, Optional, Any, Tuple, AsyncIterator, AsyncGenerator, Set, Deque
from contextlib import asynccontextmanager

import httpx
import aiosqlite
from .database import SchemaDao, EventsWriteDao, AggregatesDao, DatabaseManager
from .event import GitHubEvent
from collections import defaultdict, deque
from typing import DefaultDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubEventsCollector:
	"""
	GitHub Events Collector
	
	Handles fetching events from GitHub API, filtering, and storing in SQLite database.
	Provides methods for calculating metrics on stored events.
	"""
	
	# Events we're interested in monitoring - expanded for comprehensive monitoring
	MONITORED_EVENTS = {
		# Core development events
		'WatchEvent',           # Stars/watching repositories
		'PullRequestEvent',     # Pull requests opened/closed/merged
		'IssuesEvent',          # Issues opened/closed/labeled
		'PushEvent',           # Code pushes to repositories
		'ForkEvent',           # Repository forks
		'CreateEvent',         # Branch/tag creation
		'DeleteEvent',         # Branch/tag deletion
		'ReleaseEvent',        # Releases published
		
		# Collaboration events
		'CommitCommentEvent',  # Comments on commits
		'IssueCommentEvent',   # Comments on issues
		'PullRequestReviewEvent',      # PR reviews
		'PullRequestReviewCommentEvent', # Comments on PR reviews
		
		# Repository management events
		'PublicEvent',         # Repository made public
		'MemberEvent',         # Collaborators added/removed
		'TeamAddEvent',        # Teams added to repositories
		
		# Security and maintenance events
		'GollumEvent',         # Wiki pages created/updated
		'DeploymentEvent',     # Deployments created
		'DeploymentStatusEvent', # Deployment status updates
		'StatusEvent',         # Commit status updates
		'CheckRunEvent',       # Check runs completed
		'CheckSuiteEvent',     # Check suites completed
		
		# GitHub-specific events
		'SponsorshipEvent',    # Sponsorship changes
		'MarketplacePurchaseEvent', # Marketplace purchases
	}
	
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
		# Events provider composed here
		self._provider = GitHubEventsProvider(self._dbm)
		# Runtime monitors registry (lightweight, in-memory)
		self._monitors: Dict[int, GithubEventsMonitor] = {}
		self._next_monitor_id: int = 1
		
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
		except Exception:
			raise
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
	
	async def get_event_counts_timeseries(
		self,
		hours: int = 24,
		bucket_minutes: int = 60,
		repo_name: Optional[str] = None,
	) -> List[Dict[str, Any]]:
		"""
		Return a simple time-series of total events per bucket.

		Args:
			hours: Window to look back
			bucket_minutes: Size of each time bucket in minutes
			repo_name: Optional repository filter ("owner/repo"). If provided, counts
				are limited to that repository; otherwise counts are global.

		Returns:
			List of dicts: [{"bucket_start": iso, "total": n}] ordered by time.
		"""
		from datetime import timedelta
		if bucket_minutes <= 0:
			bucket_minutes = 60
		cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
		aggregates = self._dbm.aggregates
		return await aggregates.get_event_counts_timeseries(cutoff_time, bucket_minutes, repo_name)
	
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

	# -------------------------
	# Enhanced Monitoring Use Cases
	# -------------------------

	async def get_repository_health_score(self, repo_name: str, hours: int = 168) -> Dict[str, Any]:
		"""
		Calculate comprehensive repository health score based on multiple metrics.
		
		Args:
			repo_name: Repository name
			hours: Time window for analysis (default: 1 week)
			
		Returns:
			Dictionary with health metrics and scores
		"""
		cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
		aggregates = self._dbm.aggregates
		
		# Get activity data
		activity_data, total_events = await aggregates.get_repository_activity_summary(repo_name, cutoff_time)
		
		# Calculate health metrics
		health_metrics = {
			'repo_name': repo_name,
			'analysis_period_hours': hours,
			'total_events': total_events,
			'activity_breakdown': activity_data,
			'health_score': 0.0,
			'activity_score': 0.0,
			'collaboration_score': 0.0,
			'maintenance_score': 0.0,
			'security_score': 0.0,
			'timestamp': datetime.now(timezone.utc).isoformat()
		}
		
		# Calculate activity score (0-100)
		activity_events = ['PushEvent', 'PullRequestEvent', 'IssuesEvent', 'CreateEvent', 'DeleteEvent']
		activity_count = sum(activity_data.get(event, 0) for event in activity_events)
		health_metrics['activity_score'] = min(100.0, (activity_count / max(1, hours)) * 10)
		
		# Calculate collaboration score (0-100)
		collab_events = ['PullRequestReviewEvent', 'IssueCommentEvent', 'PullRequestReviewCommentEvent', 'CommitCommentEvent']
		collab_count = sum(activity_data.get(event, 0) for event in collab_events)
		health_metrics['collaboration_score'] = min(100.0, (collab_count / max(1, total_events)) * 100)
		
		# Calculate maintenance score (0-100)
		maintenance_events = ['ReleaseEvent', 'DeploymentEvent', 'StatusEvent', 'CheckRunEvent']
		maintenance_count = sum(activity_data.get(event, 0) for event in maintenance_events)
		health_metrics['maintenance_score'] = min(100.0, (maintenance_count / max(1, hours)) * 20)
		
		# Calculate security score (0-100) - higher is better
		security_events = ['CheckSuiteEvent', 'StatusEvent', 'DeploymentStatusEvent']
		security_count = sum(activity_data.get(event, 0) for event in security_events)
		health_metrics['security_score'] = min(100.0, (security_count / max(1, hours)) * 15)
		
		# Calculate overall health score (weighted average)
		weights = {'activity': 0.3, 'collaboration': 0.25, 'maintenance': 0.25, 'security': 0.2}
		health_metrics['health_score'] = (
			health_metrics['activity_score'] * weights['activity'] +
			health_metrics['collaboration_score'] * weights['collaboration'] +
			health_metrics['maintenance_score'] * weights['maintenance'] +
			health_metrics['security_score'] * weights['security']
		)
		
		return health_metrics

	async def get_developer_productivity_metrics(self, repo_name: str, hours: int = 168) -> List[Dict[str, Any]]:
		"""
		Analyze developer productivity metrics for a repository.
		
		Args:
			repo_name: Repository name
			hours: Time window for analysis
			
		Returns:
			List of developer productivity metrics
		"""
		cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
		
		# Get events grouped by actor
		async with self._get_db_connection() as db:
			query = """
			SELECT 
				actor_login,
				event_type,
				COUNT(*) as event_count,
				MIN(created_at) as first_activity,
				MAX(created_at) as last_activity
			FROM events 
			WHERE repo_name = ? AND created_at >= ?
			GROUP BY actor_login, event_type
			ORDER BY actor_login, event_count DESC
			"""
			
			cursor = await db.execute(query, (repo_name, cutoff_time.isoformat()))
			rows = await cursor.fetchall()
			
		# Process developer metrics
		developer_stats = defaultdict(lambda: {
			'actor_login': '',
			'total_events': 0,
			'pushes': 0,
			'prs_opened': 0,
			'issues_opened': 0,
			'reviews_given': 0,
			'comments_made': 0,
			'releases': 0,
			'first_activity': None,
			'last_activity': None,
			'event_diversity': 0,
			'productivity_score': 0.0
		})
		
		for row in rows:
			actor = row[0]
			event_type = row[1]
			count = row[2]
			
			developer_stats[actor]['actor_login'] = actor
			developer_stats[actor]['total_events'] += count
			developer_stats[actor]['first_activity'] = row[3]
			developer_stats[actor]['last_activity'] = row[4]
			
			# Map event types to productivity metrics
			if event_type == 'PushEvent':
				developer_stats[actor]['pushes'] += count
			elif event_type == 'PullRequestEvent':
				developer_stats[actor]['prs_opened'] += count
			elif event_type == 'IssuesEvent':
				developer_stats[actor]['issues_opened'] += count
			elif event_type == 'PullRequestReviewEvent':
				developer_stats[actor]['reviews_given'] += count
			elif event_type in ['IssueCommentEvent', 'PullRequestReviewCommentEvent', 'CommitCommentEvent']:
				developer_stats[actor]['comments_made'] += count
			elif event_type == 'ReleaseEvent':
				developer_stats[actor]['releases'] += count
		
		# Calculate productivity scores
		result = []
		for actor, stats in developer_stats.items():
			# Event diversity score (more diverse activity = higher score)
			event_types = ['pushes', 'prs_opened', 'issues_opened', 'reviews_given', 'comments_made', 'releases']
			active_types = sum(1 for et in event_types if stats[et] > 0)
			stats['event_diversity'] = (active_types / len(event_types)) * 100
			
			# Productivity score (weighted combination of activities)
			stats['productivity_score'] = (
				stats['pushes'] * 2.0 +
				stats['prs_opened'] * 5.0 +
				stats['reviews_given'] * 3.0 +
				stats['comments_made'] * 1.0 +
				stats['releases'] * 10.0 +
				stats['event_diversity'] * 0.5
			)
			
			result.append(stats)
		
		# Sort by productivity score
		result.sort(key=lambda x: x['productivity_score'], reverse=True)
		return result

	async def get_security_monitoring_report(self, repo_name: str, hours: int = 168) -> Dict[str, Any]:
		"""
		Generate security monitoring report for a repository.
		
		Args:
			repo_name: Repository name
			hours: Time window for analysis
			
		Returns:
			Security monitoring report
		"""
		cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
		
		async with self._get_db_connection() as db:
			# Get security-related events
			security_query = """
			SELECT event_type, COUNT(*) as count, payload
			FROM events 
			WHERE repo_name = ? AND created_at >= ?
			AND event_type IN ('CheckRunEvent', 'CheckSuiteEvent', 'StatusEvent', 'DeploymentStatusEvent', 'PublicEvent', 'MemberEvent')
			GROUP BY event_type
			"""
			
			cursor = await db.execute(security_query, (repo_name, cutoff_time.isoformat()))
			security_events = await cursor.fetchall()
			
			# Get deployment events for security analysis
			deployment_query = """
			SELECT payload, created_at
			FROM events 
			WHERE repo_name = ? AND created_at >= ?
			AND event_type = 'DeploymentEvent'
			ORDER BY created_at DESC
			"""
			
			cursor = await db.execute(deployment_query, (repo_name, cutoff_time.isoformat()))
			deployments = await cursor.fetchall()
		
		security_report = {
			'repo_name': repo_name,
			'analysis_period_hours': hours,
			'security_events': {},
			'deployment_security': {
				'total_deployments': len(deployments),
				'environments': defaultdict(int),
				'recent_deployments': []
			},
			'security_score': 0.0,
			'risk_level': 'unknown',
			'recommendations': [],
			'timestamp': datetime.now(timezone.utc).isoformat()
		}
		
		# Process security events
		total_security_events = 0
		for event_type, count, payload in security_events:
			security_report['security_events'][event_type] = count
			total_security_events += count
		
		# Analyze deployments
		for payload_str, created_at in deployments:
			try:
				payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
				env = payload.get('deployment', {}).get('environment', 'unknown')
				security_report['deployment_security']['environments'][env] += 1
				
				if len(security_report['deployment_security']['recent_deployments']) < 5:
					security_report['deployment_security']['recent_deployments'].append({
						'environment': env,
						'created_at': created_at,
						'status': payload.get('deployment', {}).get('state', 'unknown')
					})
			except (json.JSONDecodeError, TypeError):
				continue
		
		# Calculate security score
		check_events = security_report['security_events'].get('CheckRunEvent', 0) + \
					  security_report['security_events'].get('CheckSuiteEvent', 0)
		status_events = security_report['security_events'].get('StatusEvent', 0)
		
		security_report['security_score'] = min(100.0, (check_events + status_events) / max(1, hours) * 20)
		
		# Determine risk level
		if security_report['security_score'] >= 80:
			security_report['risk_level'] = 'low'
		elif security_report['security_score'] >= 50:
			security_report['risk_level'] = 'medium'
		else:
			security_report['risk_level'] = 'high'
		
		# Generate recommendations
		if check_events == 0:
			security_report['recommendations'].append("Consider setting up automated security checks")
		if security_report['deployment_security']['total_deployments'] == 0:
			security_report['recommendations'].append("No deployments detected - consider implementing CI/CD")
		if security_report['security_events'].get('PublicEvent', 0) > 0:
			security_report['recommendations'].append("Repository was made public - review access controls")
		
		return security_report

	async def detect_event_anomalies(self, repo_name: str, hours: int = 168) -> List[Dict[str, Any]]:
		"""
		Detect anomalies in event patterns for a repository.
		
		Args:
			repo_name: Repository name
			hours: Time window for analysis
			
		Returns:
			List of detected anomalies
		"""
		cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
		
		async with self._get_db_connection() as db:
			# Get hourly event counts
			query = """
			SELECT 
				strftime('%Y-%m-%d %H:00:00', created_at) as hour_bucket,
				event_type,
				COUNT(*) as count
			FROM events 
			WHERE repo_name = ? AND created_at >= ?
			GROUP BY hour_bucket, event_type
			ORDER BY hour_bucket, event_type
			"""
			
			cursor = await db.execute(query, (repo_name, cutoff_time.isoformat()))
			rows = await cursor.fetchall()
		
		# Process data for anomaly detection
		event_data = defaultdict(list)
		for hour, event_type, count in rows:
			event_data[event_type].append(count)
		
		anomalies = []
		
		for event_type, counts in event_data.items():
			if len(counts) < 3:  # Need at least 3 data points
				continue
			
			# Calculate basic statistics
			mean_count = statistics.mean(counts)
			if len(counts) > 1:
				stdev_count = statistics.stdev(counts)
			else:
				stdev_count = 0
			
			max_count = max(counts)
			min_count = min(counts)
			
			# Detect spikes (values > mean + 2*stdev)
			if stdev_count > 0 and max_count > mean_count + 2 * stdev_count:
				anomalies.append({
					'type': 'spike',
					'event_type': event_type,
					'severity': 'high' if max_count > mean_count + 3 * stdev_count else 'medium',
					'description': f'Unusual spike in {event_type} activity',
					'threshold': mean_count + 2 * stdev_count,
					'actual_value': max_count,
					'confidence': 0.95,
					'detected_at': datetime.now(timezone.utc).isoformat()
				})
			
			# Detect drops (values < mean - 2*stdev, but only if mean is significant)
			if stdev_count > 0 and mean_count > 5 and min_count < max(0, mean_count - 2 * stdev_count):
				anomalies.append({
					'type': 'drop',
					'event_type': event_type,
					'severity': 'medium',
					'description': f'Unusual drop in {event_type} activity',
					'threshold': mean_count - 2 * stdev_count,
					'actual_value': min_count,
					'confidence': 0.85,
					'detected_at': datetime.now(timezone.utc).isoformat()
				})
		
		return anomalies

	async def get_release_deployment_metrics(self, repo_name: str, hours: int = 720) -> Dict[str, Any]:
		"""
		Analyze release and deployment patterns for a repository.
		
		Args:
			repo_name: Repository name
			hours: Time window for analysis (default: 30 days)
			
		Returns:
			Release and deployment metrics
		"""
		cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
		
		async with self._get_db_connection() as db:
			# Get release events
			release_query = """
			SELECT payload, created_at
			FROM events 
			WHERE repo_name = ? AND created_at >= ?
			AND event_type = 'ReleaseEvent'
			ORDER BY created_at DESC
			"""
			
			cursor = await db.execute(release_query, (repo_name, cutoff_time.isoformat()))
			releases = await cursor.fetchall()
			
			# Get deployment events
			deployment_query = """
			SELECT payload, created_at
			FROM events 
			WHERE repo_name = ? AND created_at >= ?
			AND event_type IN ('DeploymentEvent', 'DeploymentStatusEvent')
			ORDER BY created_at DESC
			"""
			
			cursor = await db.execute(deployment_query, (repo_name, cutoff_time.isoformat()))
			deployments = await cursor.fetchall()
		
		metrics = {
			'repo_name': repo_name,
			'analysis_period_hours': hours,
			'releases': {
				'total_count': len(releases),
				'frequency_per_week': (len(releases) / (hours / 168)) if hours > 0 else 0,
				'recent_releases': [],
				'release_types': defaultdict(int)
			},
			'deployments': {
				'total_count': len(deployments),
				'frequency_per_week': (len(deployments) / (hours / 168)) if hours > 0 else 0,
				'environments': defaultdict(int),
				'success_rate': 0.0,
				'recent_deployments': []
			},
			'deployment_lead_time': 0.0,  # Average time from release to deployment
			'timestamp': datetime.now(timezone.utc).isoformat()
		}
		
		# Process releases
		release_times = []
		for payload_str, created_at in releases[:10]:  # Recent 10 releases
			try:
				payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
				release_info = payload.get('release', {})
				
				metrics['releases']['recent_releases'].append({
					'tag_name': release_info.get('tag_name', 'unknown'),
					'name': release_info.get('name', ''),
					'prerelease': release_info.get('prerelease', False),
					'created_at': created_at
				})
				
				# Track release types
				if release_info.get('prerelease', False):
					metrics['releases']['release_types']['prerelease'] += 1
				else:
					metrics['releases']['release_types']['stable'] += 1
				
				release_times.append(datetime.fromisoformat(created_at.replace('Z', '+00:00')))
			except (json.JSONDecodeError, TypeError, ValueError):
				continue
		
		# Process deployments
		successful_deployments = 0
		deployment_times = []
		for payload_str, created_at in deployments[:20]:  # Recent 20 deployments
			try:
				payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
				deployment_info = payload.get('deployment', {})
				
				env = deployment_info.get('environment', 'unknown')
				status = deployment_info.get('state', 'unknown')
				
				metrics['deployments']['environments'][env] += 1
				
				if len(metrics['deployments']['recent_deployments']) < 10:
					metrics['deployments']['recent_deployments'].append({
						'environment': env,
						'status': status,
						'created_at': created_at
					})
				
				if status in ['success', 'active']:
					successful_deployments += 1
				
				deployment_times.append(datetime.fromisoformat(created_at.replace('Z', '+00:00')))
			except (json.JSONDecodeError, TypeError, ValueError):
				continue
		
		# Calculate success rate
		if len(deployments) > 0:
			metrics['deployments']['success_rate'] = (successful_deployments / len(deployments)) * 100
		
		# Calculate deployment lead time (average time between releases and deployments)
		if release_times and deployment_times:
			lead_times = []
			for release_time in release_times:
				# Find next deployment after this release
				next_deployments = [dt for dt in deployment_times if dt > release_time]
				if next_deployments:
					lead_time = (min(next_deployments) - release_time).total_seconds() / 3600  # hours
					lead_times.append(lead_time)
			
			if lead_times:
				metrics['deployment_lead_time'] = statistics.mean(lead_times)
		
		return metrics

	async def get_community_engagement_metrics(self, repo_name: str, hours: int = 168) -> Dict[str, Any]:
		"""
		Analyze community engagement metrics for a repository.
		
		Args:
			repo_name: Repository name
			hours: Time window for analysis
			
		Returns:
			Community engagement metrics
		"""
		cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
		
		async with self._get_db_connection() as db:
			# Get engagement events
			engagement_query = """
			SELECT 
				actor_login,
				event_type,
				COUNT(*) as count,
				MIN(created_at) as first_seen,
				MAX(created_at) as last_seen
			FROM events 
			WHERE repo_name = ? AND created_at >= ?
			AND event_type IN ('WatchEvent', 'ForkEvent', 'IssuesEvent', 'PullRequestEvent', 
							  'IssueCommentEvent', 'PullRequestReviewEvent', 'CommitCommentEvent')
			GROUP BY actor_login, event_type
			ORDER BY actor_login
			"""
			
			cursor = await db.execute(engagement_query, (repo_name, cutoff_time.isoformat()))
			engagement_data = await cursor.fetchall()
		
		# Process engagement data
		contributors = defaultdict(lambda: {
			'actor_login': '',
			'total_events': 0,
			'event_types': set(),
			'first_contribution': None,
			'last_contribution': None,
			'engagement_score': 0.0
		})
		
		engagement_events = {
			'WatchEvent': 1,
			'ForkEvent': 2,
			'IssuesEvent': 3,
			'IssueCommentEvent': 2,
			'PullRequestEvent': 5,
			'PullRequestReviewEvent': 4,
			'CommitCommentEvent': 3
		}
		
		for actor, event_type, count, first_seen, last_seen in engagement_data:
			contributors[actor]['actor_login'] = actor
			contributors[actor]['total_events'] += count
			contributors[actor]['event_types'].add(event_type)
			contributors[actor]['first_contribution'] = first_seen
			contributors[actor]['last_contribution'] = last_seen
			
			# Calculate engagement score
			weight = engagement_events.get(event_type, 1)
			contributors[actor]['engagement_score'] += count * weight
		
		# Convert to list and calculate additional metrics
		contributor_list = []
		for actor, data in contributors.items():
			data['event_types'] = list(data['event_types'])
			data['event_diversity'] = len(data['event_types'])
			contributor_list.append(data)
		
		# Sort by engagement score
		contributor_list.sort(key=lambda x: x['engagement_score'], reverse=True)
		
		metrics = {
			'repo_name': repo_name,
			'analysis_period_hours': hours,
			'total_contributors': len(contributor_list),
			'new_contributors': len([c for c in contributor_list 
									if c['first_contribution'] and 
									datetime.fromisoformat(c['first_contribution'].replace('Z', '+00:00')) >= cutoff_time]),
			'active_contributors': len([c for c in contributor_list if c['total_events'] >= 3]),
			'top_contributors': contributor_list[:10],
			'engagement_distribution': {
				'high_engagement': len([c for c in contributor_list if c['engagement_score'] >= 20]),
				'medium_engagement': len([c for c in contributor_list if 5 <= c['engagement_score'] < 20]),
				'low_engagement': len([c for c in contributor_list if c['engagement_score'] < 5])
			},
			'community_health_score': 0.0,
			'timestamp': datetime.now(timezone.utc).isoformat()
		}
		
		# Calculate community health score
		total_contributors = max(1, metrics['total_contributors'])
		active_ratio = metrics['active_contributors'] / total_contributors
		new_contributor_ratio = metrics['new_contributors'] / total_contributors
		high_engagement_ratio = metrics['engagement_distribution']['high_engagement'] / total_contributors
		
		metrics['community_health_score'] = (
			active_ratio * 40 +
			new_contributor_ratio * 30 +
			high_engagement_ratio * 30
		) * 100
		
		return metrics

	# -------------------------
	# EventDict functionality
	# -------------------------

	class EventDict:
		"""Dictionary keyed by event type containing lists of GitHubEvent."""

		def __init__(self) -> None:
			self._by_type: DefaultDict[str, List[GitHubEvent]] = defaultdict(list)

		def add(self, event: GitHubEvent) -> None:
			self._by_type[event.event_type].append(event)

		def extend(self, events: List[GitHubEvent]) -> None:
			for e in events:
				self.add(e)

		def get(self, event_type: str) -> List[GitHubEvent]:
			return list(self._by_type.get(event_type, []))

		def types(self) -> List[str]:
			return list(self._by_type.keys())

		def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
			return {k: [e.to_dict() for e in v] for k, v in self._by_type.items()}

	async def get_event_dict_since(self, since: datetime) -> "GitHubEventsCollector.EventDict":
		"""Delegate to provider to fetch grouped events since timestamp."""
		return await self._provider.get_event_dict_since(since)

	async def get_event_dict_recent(self, offset_minutes: int = 60) -> "GitHubEventsCollector.EventDict":
		"""Fetch recent events grouped by type."""
		if offset_minutes <= 0:
			offset_minutes = 1
		since = datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)
		return await self._provider.get_event_dict_since(since)


class GitHubEventsProvider:
	"""Provides EventDict structures backed by DAOs owned via DatabaseManager."""

	def __init__(self, db_manager: DatabaseManager) -> None:
		self._dbm = db_manager

	class EventDict(GitHubEventsCollector.EventDict):
		pass

	async def get_event_dict_since(self, since: datetime) -> GitHubEventsCollector.EventDict:
		result = GitHubEventsCollector.EventDict()
		factory = self._dbm.events
		for et in ("WatchEvent", "PullRequestEvent", "IssuesEvent"):
			dao = factory.get_dao(et)
			rows = await dao.get(repo=None, since_ts=since)
			events: List[GitHubEvent] = []
			for r in rows:
				try:
					created_at = r.get("created_at")
					if isinstance(created_at, str):
						created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
					events.append(
						GitHubEvent(
							id=str(r.get("id")),
							event_type=et,
							created_at=created_at if isinstance(created_at, datetime) else datetime.now(timezone.utc),
							repo_name=str(r.get("repo_name")),
							actor_login=str(r.get("actor_login")),
							payload=r.get("payload", {}) or {},
						)
					)
				except Exception:
					continue
			result.extend(events)
		return result


class GithubEventsMonitor:
	"""Instance-based in-memory monitor for a specific repository."""

	def __init__(self, repository: str, monitored_events: Set[str], github_token: Optional[str] = None, interval_seconds: int = 60) -> None:
		self.repository = repository
		self.monitored_events = set(monitored_events)
		self._token = github_token
		self._interval = int(interval_seconds)
		self._events: Deque[Dict[str, Any]] = deque()
		self._task: Optional[asyncio.Task] = None
		self.started_at: Optional[str] = None

	async def _poll_loop(self) -> None:
		repo = self.repository
		interval = self._interval
		allowed: Set[str] = self.monitored_events
		etag: Optional[str] = None
		url = f"https://api.github.com/repos/{repo}/events"
		headers = {
			"Accept": "application/vnd.github+json",
			"X-GitHub-Api-Version": "2022-11-28",
			"User-Agent": "github-events-monitor/1.0",
		}
		if self._token:
			headers["Authorization"] = f"Bearer {self._token}"
		async with httpx.AsyncClient(timeout=30.0) as client:
			while self._task is not None:
				try:
					_h = dict(headers)
					if etag:
						_h["If-None-Match"] = etag
					resp = await client.get(url, headers=_h)
					if resp.status_code == 304:
						await asyncio.sleep(max(5, interval))
						continue
					resp.raise_for_status()
					etag = resp.headers.get("ETag", etag)
					data = resp.json() or []
					for e in data:
						if e.get("type") not in allowed:
							continue
						self._events.appendleft({
							"id": e.get("id"),
							"type": e.get("type"),
							"repo": (e.get("repo") or {}).get("name"),
							"actor": (e.get("actor") or {}).get("login"),
							"created_at": e.get("created_at"),
						})
						if len(self._events) > 1000:
							self._events.pop()
				except Exception:
					await asyncio.sleep(max(10, interval))
				else:
					await asyncio.sleep(max(5, interval))

	def start(self) -> None:
		if self._task is not None:
			return
		self.started_at = datetime.now(timezone.utc).isoformat()
		self._task = asyncio.create_task(self._poll_loop())

	def stop(self) -> None:
		task = self._task
		self._task = None
		if task and not task.done():
			task.cancel()

	@property
	def buffer_size(self) -> int:
		return len(self._events)

	def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
		limit = max(1, min(int(limit or 100), 1000))
		return list(self._events)[:limit]

	def get(self) -> "GitHubEventsCollector.EventDict":
		"""Return buffered events grouped by type as EventDict of GitHubEvent."""
		result = GitHubEventsCollector.EventDict()
		for e in list(self._events):
			try:
				created_at = e.get("created_at")
				if isinstance(created_at, str):
					created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
				gh = GitHubEvent(
					id=str(e.get("id")),
					event_type=str(e.get("type")),
					created_at=created_at if isinstance(created_at, datetime) else datetime.now(timezone.utc),
					repo_name=str(e.get("repo")),
					actor_login=str(e.get("actor")),
					payload={},
				)
				result.add(gh)
			except Exception:
				continue
		return result

	# -------------------------
	# Runtime monitor management
	# -------------------------

	def start_monitor(
		self,
		repository: str = "sparesparrow/mcp-prompts",
		monitored_events: Set[str] = {"WatchEvent", "PullRequestEvent", "IssuesEvent"},
		interval_seconds: int = 60,
	) -> int:
		"""Start a background monitor and return its id."""
		mon_id = self._next_monitor_id
		self._next_monitor_id += 1
		monitor = GithubEventsMonitor(
			repository=repository,
			monitored_events=set(monitored_events),
			github_token=self.github_token,
			interval_seconds=interval_seconds,
		)
		monitor.start()
		self._monitors[mon_id] = monitor
		return mon_id

	def stop_monitor(self, mon_id: int) -> bool:
		"""Stop a running monitor by id."""
		mon = self._monitors.pop(mon_id, None)
		if not mon:
			return False
		mon.stop()
		return True

	def get_active_monitors(self) -> List[Dict[str, Any]]:
		"""List active monitors with basic metadata."""
		out: List[Dict[str, Any]] = []
		for mid, m in self._monitors.items():
			out.append({
				"id": mid,
				"repository": m.repository,
				"monitored_events": sorted(m.monitored_events),
				"buffer_size": m.buffer_size,
				"started_at": m.started_at,
			})
		return out

	def get_events(self, mon_id: int, limit: int = 100) -> List[Dict[str, Any]]:
		"""Get most recent collected events for a monitor id."""
		m = self._monitors.get(mon_id)
		if not m:
			return []
		return m.get_events(limit)

	def get_events_grouped(self, mon_id: int) -> "GitHubEventsCollector.EventDict":
		"""Group buffered monitor events by type and return EventDict."""
		m = self._monitors.get(mon_id)
		result = GitHubEventsCollector.EventDict()
		if not m:
			return result
		grouped = m.get()
		# grouped is already EventDict, but ensure same type
		for et in grouped.types():
			for ev in grouped.get(et):
				result.add(ev)
		return result

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


