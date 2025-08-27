"""
GitHub Events Monitor - REST API

FastAPI application providing REST endpoints for GitHub Events monitoring metrics.
"""

import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Awaitable, Callable, Union, Protocol, runtime_checkable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, Request
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi import Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import io
import logging
import aiosqlite
from enum import Enum, auto

from .event_collector import GitHubEventsCollector
from pathlib import Path
# MCP integration may live outside the package after cleanup; import defensively
try:
	from . import mcp_server as mcp_mod  # type: ignore
except Exception:  # pragma: no cover - optional dependency
	mcp_mod = None  # type: ignore
from .database import EventsDaoFactory, AggregatesDao


def _route_exists(target, path: str, method: str) -> bool:
	"""Check if a route with the same path+method already exists on target."""
	method = method.upper()
	for r in target.routes:
		try:
			if getattr(r, "path", None) == path and method in getattr(r, "methods", set()):
				return True
		except Exception:
			continue
	return False


def _register_endpoints_safely(app: FastAPI) -> None:
	"""Register endpoint classes using existing handler functions without duplicating routes."""
	# Pairs allow optional dispatcher registration to align with README class diagram
	endpoint_pairs = [
		("HEALTH", HealthEndpoint(handler=health_check)),
		("COLLECT", CollectEndpoint(handler=manual_collect)),
		("WEBHOOK", WebhookEndpoint(handler=github_webhook)),
		("EVENT_COUNTS", MetricsEventCountsEndpoint(handler=get_event_counts)),
		("PR_INTERVAL", MetricsPrIntervalEndpoint(handler=get_pr_interval)),
		("REPO_ACTIVITY_SUMMARY", MetricsRepositoryActivityEndpoint(handler=get_repository_activity)),
		("TRENDING_REPOS", MetricsTrendingEndpoint(handler=get_trending_repositories)),
		("TRENDING_CHART", VisualizationTrendingChartEndpoint(handler=get_trending_chart)),
		("PR_TIMELINE", VisualizationPrTimelineEndpoint(handler=get_pr_timeline_chart)),
		("EVENTS_TIMESERIES", EventsTimeseriesEndpoint(handler=get_events_timeseries)),
		("START_MONITOR", StartMonitorEndpoint(handler=start_monitor)),
		("STOP_MONITOR", StopMonitorEndpoint(handler=stop_monitor)),
		("ACTIVE_MONITORS", ActiveMonitorsEndpoint(handler=get_active_monitors)),
		("MONITOR_EVENTS", MonitorEventsEndpoint(handler=get_monitor_events)),
		("MONITOR_EVENTS_GROUPED", MonitorEventsGroupedEndpoint(handler=get_monitor_events_grouped)),
		("MCP_CAPABILITIES", McpCapabilitiesEndpoint(handler=get_mcp_capabilities)),
		("MCP_TOOLS", McpToolsEndpoint(handler=list_mcp_tools)),
		("MCP_RESOURCES", McpResourcesEndpoint(handler=list_mcp_resources)),
		("MCP_PROMPTS", McpPromptsEndpoint(handler=list_mcp_prompts)),
	]
	for et, ep in endpoint_pairs:
		if not _route_exists(app, ep.path, ep.method):
			ep.register(app)
		# Best-effort dispatcher registration (created later in this module)
		try:
			dispatcher.register_endpoint(getattr(EndpointType, et), ep)  # type: ignore[name-defined]
		except Exception:
			pass


# ------------------------- Inlined API Endpoints -----------------------------

HttpHandler = Callable[..., Awaitable[Any]]
RouteTarget = Union[FastAPI, 'APIRouter']


class ApiEndpoint:
	"""Base class for REST API endpoints.
	
	Encapsulates route metadata and provides a method to register the endpoint
	on a FastAPI application or router.
	"""
	
	def __init__(self, path: str, method: str, name: str, summary: str, handler: Optional[HttpHandler] = None) -> None:
		self.path = path
		self.method = method.upper()
		self.name = name
		self.summary = summary
		self._handler = handler
	
	def get_handler(self) -> HttpHandler:
		"""Return the async handler callable for this endpoint."""
		if self._handler is None:
			async def _not_configured(**kwargs: Any) -> Dict[str, Any]:
				return {"error": f"{self.name} handler not configured", **kwargs}
			return _not_configured
		return self._handler
	
	def register(self, target: RouteTarget) -> None:
		"""Register this endpoint on the provided FastAPI app or APIRouter."""
		target.add_api_route(
			self.path,
			self.get_handler(),
			methods=[self.method],
			name=self.name,
			summary=self.summary,
		)


class HealthEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/health",
			method="GET",
			name="health_check",
			summary="Service health check",
			handler=handler,
		)


class CollectEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/collect",
			method="POST",
			name="manual_collect",
			summary="Manually trigger event collection",
			handler=handler,
		)


class WebhookEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/webhook",
			method="POST",
			name="github_webhook",
			summary="Optional GitHub webhook receiver",
			handler=handler,
		)


class MetricsEventCountsEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/event-counts",
			method="GET",
			name="get_event_counts",
			summary="Get event counts by type",
			handler=handler,
		)


class MetricsPrIntervalEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/pr-interval",
			method="GET",
			name="get_pr_interval",
			summary="Get average PR interval for a repository",
			handler=handler,
		)


class MetricsRepositoryActivityEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/repository-activity",
			method="GET",
			name="get_repository_activity",
			summary="Get activity summary for a repository",
			handler=handler,
		)


class MetricsTrendingEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/trending",
			method="GET",
			name="get_trending_repositories",
			summary="Get trending repositories by event count",
			handler=handler,
		)


class VisualizationTrendingChartEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/visualization/trending-chart",
			method="GET",
			name="get_trending_chart",
			summary="Generate trending repositories chart",
			handler=handler,
		)


class VisualizationPrTimelineEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/visualization/pr-timeline",
			method="GET",
			name="get_pr_timeline_chart",
			summary="Generate PR timeline chart for a repository",
			handler=handler,
		)


class McpCapabilitiesEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/mcp/capabilities",
			method="GET",
			name="get_mcp_capabilities",
			summary="List MCP tools, resources, and prompts",
			handler=handler,
		)


class McpToolsEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/mcp/tools",
			method="GET",
			name="list_mcp_tools",
			summary="List MCP tools",
			handler=handler,
		)


class McpResourcesEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/mcp/resources",
			method="GET",
			name="list_mcp_resources",
			summary="List MCP resources",
			handler=handler,
		)


class McpPromptsEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/mcp/prompts",
			method="GET",
			name="list_mcp_prompts",
			summary="List MCP prompts",
			handler=handler,
		)


# ------------------------- EndpointType & Dispatcher -------------------------

class EndpointType(Enum):
	"""Enumeration of supported endpoint types (aligns with README)."""
	HEALTH = auto()
	COLLECT = auto()
	WEBHOOK = auto()
	EVENT_COUNTS = auto()
	PR_INTERVAL = auto()
	REPO_ACTIVITY_SUMMARY = auto()
	TRENDING_REPOS = auto()
	TRENDING_CHART = auto()
	PR_TIMELINE = auto()
	EVENTS_TIMESERIES = auto()
	START_MONITOR = auto()
	STOP_MONITOR = auto()
	ACTIVE_MONITORS = auto()
	MONITOR_EVENTS = auto()
	MONITOR_EVENTS_GROUPED = auto()
	MCP_CAPABILITIES = auto()
	MCP_TOOLS = auto()
	MCP_RESOURCES = auto()
	MCP_PROMPTS = auto()


class EndpointDispatcher:
	"""Holds a mapping of EndpointType to ApiEndpoint and exposes a route map."""

	def __init__(self) -> None:
		self.endpoints: Dict[EndpointType, ApiEndpoint] = {}

	def register_endpoint(self, endpoint_type: EndpointType, endpoint: ApiEndpoint) -> None:
		self.endpoints[endpoint_type] = endpoint

	def get_route_map(self) -> Dict[str, EndpointType]:
		"""Return path -> EndpointType mapping for registered endpoints."""
		return {ep.path: et for et, ep in self.endpoints.items()}


# Global dispatcher instance (populated during registration)
dispatcher = EndpointDispatcher()


# ------------------------- Additional Endpoint Classes ----------------------

class EventsTimeseriesEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/events-timeseries",
			method="GET",
			name="get_events_timeseries",
			summary="Alias of event-counts-timeseries (JSON timeseries)",
			handler=handler,
		)


class StartMonitorEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/monitors/start",
			method="POST",
			name="start_monitor",
			summary="Start a runtime repo monitor",
			handler=handler,
		)


class StopMonitorEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/monitors/{mon_id}/stop",
			method="POST",
			name="stop_monitor",
			summary="Stop a runtime repo monitor",
			handler=handler,
		)


class ActiveMonitorsEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/monitors",
			method="GET",
			name="get_active_monitors",
			summary="List active runtime monitors",
			handler=handler,
		)


class MonitorEventsEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/monitors/{mon_id}/events",
			method="GET",
			name="get_monitor_events",
			summary="List recent buffered events for a monitor",
			handler=handler,
		)


class MonitorEventsGroupedEndpoint(ApiEndpoint):
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/monitors/{mon_id}/events/grouped",
			method="GET",
			name="get_monitor_events_grouped",
			summary="Return grouped (by type) buffered events for a monitor",
			handler=handler,
		)
# ------------------------- Inlined Services Layer ----------------------------

logger = logging.getLogger(__name__)


class EventsRepository:
	"""Component: EventsRepository - SQLite queries (read-only for API)"""
	
	def __init__(self, db_path: str):
		self.db_path = db_path
		self.dao_factory = EventsDaoFactory(db_path)
		self.aggregates = AggregatesDao(db_path)
	
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
		return await self.aggregates.get_trending_since(since_ts, limit)
	
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

	async def event_counts_timeseries(
		self,
		since_ts: datetime,
		bucket_minutes: int = 5,
		repo: Optional[str] = None,
	) -> List[Dict[str, Any]]:
		"""Return total events per time bucket from since_ts to now."""
		return await self.aggregates.get_event_counts_timeseries(since_ts, bucket_minutes, repo)


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
	
	async def get_pr_interval(self, repo: str) -> Optional[Dict[str, Any]]:
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

	async def get_event_counts_timeseries(
		self,
		hours: int,
		bucket_minutes: int,
		repo: Optional[str] = None,
	) -> List[Dict[str, Any]]:
		"""Return total events per bucket for a trailing window."""
		since_ts = self._now() - timedelta(hours=hours)
		return await self.repository.event_counts_timeseries(since_ts, bucket_minutes, repo)


class VisualizationService:
	"""Component: VisualizationService - Build images/figures (e.g., Plotly/PNG)"""
	
	def __init__(self, repository: EventsRepository):
		self.repository = repository
	
	def _build_plot(self, data: Any) -> plt.Figure:
		"""Build a matplotlib figure from data"""
		fig, ax = plt.subplots()
		return fig
	
	async def trending_chart(self, hours: int, limit: int, format: str = "png") -> bytes:
		"""Generate trending repositories chart"""
		from datetime import timedelta
		since_ts = datetime.now(timezone.utc) - timedelta(hours=hours)
		trending_data = await self.repository.trending_since(since_ts, limit)
		
		if not trending_data:
			raise ValueError("No data found for the specified time period")
		
		repo_names = [repo['repo_name'].split('/')[-1][:20] for repo in trending_data]
		event_counts = [repo['total_events'] for repo in trending_data]
		
		plt.style.use('default')
		fig, ax = plt.subplots(figsize=(12, 8))
		
		bars = ax.barh(range(len(repo_names)), event_counts, color='steelblue', alpha=0.7)
		
		ax.set_yticks(range(len(repo_names)))
		ax.set_yticklabels(repo_names)
		ax.set_xlabel('Event Count')
		ax.set_title(f'Top {len(repo_names)} Repositories (Last {hours} Hours)')
		ax.grid(axis='x', alpha=0.3)
		
		for i, (bar, count) in enumerate(zip(bars, event_counts)):
			width = bar.get_width()
			ax.text(width + max(event_counts) * 0.01, bar.get_y() + bar.get_height()/2, 
				   str(count), ha='left', va='center', fontsize=9)
		
		plt.tight_layout()
		
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
		timestamps = await self.repository.pr_timestamps(repo)
		
		if len(timestamps) < 1:
			raise ValueError("No PR data found for the specified repository")
		
		plt.style.use('default')
		fig, ax = plt.subplots(figsize=(12, 6))
		
		dates = [ts.date() for ts in timestamps]
		counts = [1] * len(dates)
		
		ax.plot(dates, counts, marker='o', color='steelblue', linewidth=2)
		ax.fill_between(dates, counts, color='steelblue', alpha=0.15)
		ax.set_xlabel('Date')
		ax.set_ylabel('PRs opened')
		ax.set_title(f"PR openings for {repo}")
		ax.grid(axis='y', alpha=0.3)
		plt.xticks(rotation=45, ha='right')
		plt.tight_layout()
		
		img_buffer = io.BytesIO()
		if format == "svg":
			plt.savefig(img_buffer, format='svg', bbox_inches='tight', dpi=150)
		else:
			plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
		
		plt.close()
		img_buffer.seek(0)
		return img_buffer.read()

	async def events_timeseries_chart(
		self,
		hours: int,
		bucket_minutes: int,
		repo: Optional[str] = None,
		format: str = "png",
	) -> bytes:
		"""Generate an events-per-bucket line chart for a repo or global."""
		from datetime import timedelta
		since_ts = datetime.now(timezone.utc) - timedelta(hours=hours)
		series = await self.repository.event_counts_timeseries(since_ts, bucket_minutes, repo)
		if not series:
			raise ValueError("No data found for the specified time period")
		x_values = [s.get("bucket_start") for s in series]
		y_values = [int(s.get("total", 0)) for s in series]
		plt.style.use('default')
		fig, ax = plt.subplots(figsize=(12, 6))
		ax.plot(x_values, y_values, color='steelblue', linewidth=2, marker='o', markersize=3)
		ax.fill_between(range(len(y_values)), y_values, color='steelblue', alpha=0.15)
		title_suffix = f" for {repo}" if repo else " (All Repos)"
		ax.set_title(f"Events per {bucket_minutes} min bucket (Last {hours}h){title_suffix}")
		ax.set_xlabel('Time (bucket start)')
		ax.set_ylabel('Events')
		ax.grid(axis='y', alpha=0.3)
		plt.xticks(rotation=45, ha='right')
		plt.tight_layout()
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
			event_count = await self.repository.aggregates.get_total_events()
			
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


# Configuration from environment variables
DATABASE_PATH = os.getenv("DATABASE_PATH", "github_events.db")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))  # 5 minutes default
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Parse target repositories
TARGET_REPOSITORIES = None
target_repos_env = os.getenv("TARGET_REPOSITORIES")
if target_repos_env:
	TARGET_REPOSITORIES = [repo.strip() for repo in target_repos_env.split(",") if repo.strip()]

# Global instances
collector_instance: Optional[GitHubEventsCollector] = None
repository_instance: Optional[EventsRepository] = None
metrics_service: Optional[MetricsService] = None
visualization_service: Optional[VisualizationService] = None
health_reporter: Optional[HealthReporter] = None

# ------------------------- Protocols (SOLID / DI) ----------------------------

@runtime_checkable
class RepositoryProtocol(Protocol):
	async def count_events_by_type(self, since_ts: datetime) -> Dict[str, int]: ...
	async def pr_timestamps(self, repo: str) -> List[datetime]: ...
	async def activity_by_repo(self, repo: str, since_ts: datetime) -> Dict[str, Any]: ...
	async def trending_since(self, since_ts: datetime, limit: int) -> List[Dict[str, Any]]: ...
	async def event_counts_timeseries(self, since_ts: datetime, bucket_minutes: int, repo: Optional[str]) -> List[Dict[str, Any]]: ...


@runtime_checkable
class MetricsServiceProtocol(Protocol):
	async def get_event_counts(self, offset_minutes: int) -> Dict[str, Any]: ...
	async def get_pr_interval(self, repo: str) -> Optional[Dict[str, Any]]: ...
	async def get_repository_activity(self, repo: str, hours: int) -> Dict[str, Any]: ...
	async def get_trending(self, hours: int, limit: int) -> List[Dict[str, Any]]: ...
	async def get_event_counts_timeseries(self, hours: int, bucket_minutes: int, repo: Optional[str]) -> List[Dict[str, Any]]: ...


@runtime_checkable
class VisualizationServiceProtocol(Protocol):
	async def trending_chart(self, hours: int, limit: int, format: str) -> bytes: ...
	async def pr_timeline(self, repo: str, format: str) -> bytes: ...
	async def events_timeseries_chart(self, hours: int, bucket_minutes: int, repo: Optional[str], format: str) -> bytes: ...


@runtime_checkable
class HealthReporterProtocol(Protocol):
	async def status(self) -> Dict[str, Any]: ...


def get_metrics_service_dep() -> MetricsServiceProtocol:
	global metrics_service
	if metrics_service is None:
		raise HTTPException(status_code=503, detail="Metrics service not initialized")
	return metrics_service


def get_visualization_service_dep() -> VisualizationServiceProtocol:
	global visualization_service
	if visualization_service is None:
		raise HTTPException(status_code=503, detail="Visualization service not initialized")
	return visualization_service


def get_health_reporter_dep() -> HealthReporterProtocol:
	global health_reporter
	if health_reporter is None:
		raise HTTPException(status_code=503, detail="Health reporter not initialized")
	return health_reporter

@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Application lifespan manager"""
	global collector_instance, repository_instance, metrics_service, visualization_service, health_reporter

	# Ensure database directory exists if a path component is provided
	try:
		db_parent = Path(DATABASE_PATH).parent
		if str(db_parent) and str(db_parent) != str(Path(DATABASE_PATH)):
			db_parent.mkdir(parents=True, exist_ok=True)
	except Exception:
		# Proceed; aiosqlite will raise if the path truly cannot be created
		pass

	# Initialize collector
	collector_instance = GitHubEventsCollector(DATABASE_PATH, GITHUB_TOKEN, target_repositories=TARGET_REPOSITORIES)
	await collector_instance.initialize_database()

	# Initialize service layer components
	repository_instance = EventsRepository(DATABASE_PATH)
	metrics_service = MetricsService(repository_instance)
	visualization_service = VisualizationService(repository_instance)
	health_reporter = HealthReporter(repository_instance)

	# Start background polling task
	polling_task = asyncio.create_task(background_poller())

	yield

	# Cleanup
	polling_task.cancel()
	try:
		await polling_task
	except asyncio.CancelledError:
		pass

# Create FastAPI app
app = FastAPI(
	title="GitHub Events Monitor",
	description="Monitor GitHub Events and provide metrics via REST API",
	version="1.0.0",
	lifespan=lifespan
)

# Wire endpoint classes to existing handlers (no-op if already present)
# Note: endpoint classes are registered at the end of this module

# CORS configuration (allow GitHub Pages and configurable origins)
_cors_origins_env = os.getenv("CORS_ORIGINS", "*")
_allow_origins = [o.strip() for o in _cors_origins_env.split(",")] if _cors_origins_env != "*" else ["*"]
app.add_middleware(
	CORSMiddleware,
	allow_origins=_allow_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Pydantic models for API responses
class EventCountsResponse(BaseModel):
	"""Response model for event counts endpoint"""
	offset_minutes: int = Field(..., description="Time offset in minutes")
	total_events: int = Field(..., description="Total number of events")
	counts: Dict[str, int] = Field(..., description="Event counts by type")
	timestamp: str = Field(..., description="Response timestamp")

class TimeSeriesPoint(BaseModel):
	"""Point in events-per-bucket series"""
	bucket_start: str = Field(..., description="Bucket start timestamp (UTC ISO)")
	total: int = Field(..., description="Total events in bucket")

class EventCountsTimeSeriesResponse(BaseModel):
	"""Response model for event counts timeseries endpoint"""
	hours: int = Field(..., description="Window size in hours")
	bucket_minutes: int = Field(..., description="Bucket size in minutes")
	repo: Optional[str] = Field(None, description="Optional repository filter")
	series: List[TimeSeriesPoint] = Field(..., description="List of bucketed counts")
	timestamp: str = Field(..., description="Response timestamp")

class PRIntervalResponse(BaseModel):
	"""Response model for PR interval endpoint"""
	repo_name: str = Field(..., description="Repository name")
	pr_count: int = Field(..., description="Number of PR events found")
	avg_interval_seconds: Optional[float] = Field(None, description="Average interval in seconds")
	avg_interval_hours: Optional[float] = Field(None, description="Average interval in hours")
	avg_interval_days: Optional[float] = Field(None, description="Average interval in days")
	median_interval_seconds: Optional[float] = Field(None, description="Median interval in seconds")
	min_interval_seconds: Optional[float] = Field(None, description="Minimum interval in seconds")
	max_interval_seconds: Optional[float] = Field(None, description="Maximum interval in seconds")

class RepositoryActivityResponse(BaseModel):
	"""Response model for repository activity endpoint"""
	repo_name: str = Field(..., description="Repository name")
	hours: int = Field(..., description="Time window in hours")
	total_events: int = Field(..., description="Total events in time window")
	activity: Dict[str, Dict[str, Any]] = Field(..., description="Activity breakdown by event type")
	timestamp: str = Field(..., description="Response timestamp")

class TrendingRepository(BaseModel):
	"""Model for trending repository data"""
	repo_name: str
	total_events: int
	watch_events: int
	pr_events: int
	issue_events: int
	first_event: str
	last_event: str

class TrendingRepositoriesResponse(BaseModel):
	"""Response model for trending repositories endpoint"""
	hours: int = Field(..., description="Time window in hours")
	repositories: List[TrendingRepository] = Field(..., description="List of trending repositories")
	timestamp: str = Field(..., description="Response timestamp")

class HealthResponse(BaseModel):
	"""Response model for health check endpoint"""
	status: str = Field(..., description="Service status")
	database_path: str = Field(..., description="Database file path")
	github_token_configured: bool = Field(..., description="Whether GitHub token is configured")
	timestamp: str = Field(..., description="Response timestamp")

# Dependency to get collector instance
async def get_collector_instance() -> GitHubEventsCollector:
	"""Dependency to get the collector instance.

	Lazily initializes a collector when not already created so routes can
	respond with validation errors (422) without failing dependency injection.
	"""
	global collector_instance
	if collector_instance is None:
		collector_instance = GitHubEventsCollector(DATABASE_PATH, GITHUB_TOKEN, target_repositories=TARGET_REPOSITORIES)
		await collector_instance.initialize_database()
	return collector_instance

# Background polling task
async def background_poller():
	"""Background task to periodically collect events"""
	while True:
		try:
			if collector_instance:
				count = await collector_instance.collect_and_store()
				if count > 0:
					print(f"Background poll collected {count} events")
		except Exception as e:
			print(f"Background polling error: {e}")
		
		# Respect GitHub's suggested poll interval if available
		poll_seconds = getattr(collector_instance, 'suggested_poll_seconds', None)
		if not poll_seconds or poll_seconds <= 0:
			poll_seconds = POLL_INTERVAL
		await asyncio.sleep(poll_seconds)

# API Endpoints

# Health endpoint removed - now registered via HealthEndpoint class only
async def health_check(hr: HealthReporterProtocol = Depends(get_health_reporter_dep)):
	"""Health check endpoint handler (registered via HealthEndpoint class)"""
	status_data = await hr.status()
	
	return HealthResponse(
		status=status_data["status"],
		database_path=DATABASE_PATH,
		github_token_configured=bool(GITHUB_TOKEN),
		timestamp=status_data["timestamp"]
	)

@app.post("/collect")
async def manual_collect(
	background_tasks: BackgroundTasks,
	limit: Optional[int] = Query(None, description="Maximum number of events to collect")
):
	"""Manually trigger event collection"""
	collector = await get_collector_instance()
	
	# Run collection in background
	async def collect_task():
		count = await collector.collect_and_store(limit)
		print(f"Manual collection stored {count} events")
	
	background_tasks.add_task(collect_task)
	
	return {"message": "Collection started", "limit": limit}

@app.post("/webhook")
async def github_webhook(
	x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
	x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
	payload: dict = None,
	collector: GitHubEventsCollector = Depends(get_collector_instance)
):
	"""
	Optional webhook receiver for GitHub events. Stores only monitored types.
	Signature verification can be added by setting a shared secret and validating
	X-Hub-Signature-256; omitted for brevity in this assignment.
	"""
	try:
		if not payload or not isinstance(payload, dict):
			return {"status": "ignored"}
		# Normalize to our schema; accept only monitored types
		event_type = x_github_event or payload.get("type")
		if event_type not in {"WatchEvent", "PullRequestEvent", "IssuesEvent"}:
			return {"status": "ignored"}
		# Convert single event into GitHubEvent and store
		from .event import GitHubEvent
		try:
			repo = payload.get("repository") or {}
			actor = payload.get("sender") or payload.get("actor") or {}
			created_at = payload.get("created_at") or datetime.now(timezone.utc).isoformat()
			ge = GitHubEvent(
				id=str(payload.get("id") or f"wh_{int(datetime.now().timestamp()*1000)}"),
				event_type=event_type,
				repo_name=str(repo.get("full_name") or repo.get("name") or "unknown/unknown"),
				actor_login=str(actor.get("login") or "unknown"),
				created_at=datetime.fromisoformat(created_at.replace('Z', '+00:00')),
				payload=payload,
			)
			affected = await collector.store_events([ge])
		except Exception:
			# Accept but ignore if payload missing required fields
			affected = 0
		return {"status": "ok", "stored": affected}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/event-counts", response_model=EventCountsResponse)
async def get_event_counts(
	offset_minutes: Optional[int] = Query(None, gt=0, description="Number of minutes to look back"),
	offset_minutes_alias: Optional[int] = Query(None, alias="offsetMinutes", gt=0, description="Number of minutes to look back (camelCase alias)"),
	ms: MetricsServiceProtocol = Depends(get_metrics_service_dep),
):
	"""
	Get total number of events grouped by event type for a given offset using MetricsService.
	
	The offset determines how much time we want to look back.
	For example, offset_minutes=10 means count events from the last 10 minutes.
	"""
	try:
		final_offset = offset_minutes_alias or offset_minutes
		if not final_offset:
			raise HTTPException(status_code=422, detail="offset_minutes or offsetMinutes is required and must be > 0")
		result = await ms.get_event_counts(int(final_offset))
		return EventCountsResponse(**result)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/pr-interval", response_model=PRIntervalResponse)
async def get_pr_interval(
	repo: str = Query(..., description="Repository name (e.g., 'owner/repo')"),
	ms: MetricsServiceProtocol = Depends(get_metrics_service_dep),
):
	"""
	Calculate the average time between pull requests for a given repository using MetricsService.
	
	Only considers PR 'opened' events for meaningful interval calculation.
	"""
	try:
		result = await ms.get_pr_interval(repo)
		
		if result is None:
			return PRIntervalResponse(
				repo_name=repo,
				pr_count=0
			)
		
		return PRIntervalResponse(**result)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/avg-pr-interval", response_model=PRIntervalResponse)
async def get_avg_pr_interval(
	repo: str = Query(..., description="Repository name (e.g., 'owner/repo')")
):
	"""Alias of /metrics/pr-interval returning the same payload shape."""
	return await get_pr_interval(repo)

@app.get("/metrics/repository-activity", response_model=RepositoryActivityResponse)
async def get_repository_activity(
	repo: str = Query(..., description="Repository name (e.g., 'owner/repo')"),
	hours: int = Query(24, gt=0, description="Number of hours to look back"),
	ms: MetricsServiceProtocol = Depends(get_metrics_service_dep),
):
	"""Get detailed activity summary for a specific repository using MetricsService"""
	try:
		result = await ms.get_repository_activity(repo, hours)
		return RepositoryActivityResponse(**result)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/trending", response_model=TrendingRepositoriesResponse)
async def get_trending_repositories(
	hours: int = Query(24, gt=0, description="Number of hours to look back"),
	limit: int = Query(10, gt=0, le=50, description="Maximum number of repositories to return"),
	ms: MetricsServiceProtocol = Depends(get_metrics_service_dep),
):
	"""Get most active repositories by event count using MetricsService"""
	try:
		trending_data = await ms.get_trending(hours, limit)
		
		repositories = [
			TrendingRepository(**repo_data) for repo_data in trending_data
		]
		
		return TrendingRepositoriesResponse(
			hours=hours,
			repositories=repositories,
			timestamp=datetime.now(timezone.utc).isoformat()
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/visualization/trending-chart")
async def get_trending_chart(
	hours: int = Query(24, gt=0, description="Number of hours to look back"),
	limit: int = Query(10, gt=0, le=20, description="Number of top repositories"),
	format: str = Query("png", pattern="^(png|svg)$", description="Image format"),
	vs: VisualizationServiceProtocol = Depends(get_visualization_service_dep),
):
	"""
	Generate a visualization chart of trending repositories using VisualizationService.
	
	This is the bonus visualization endpoint showing repository activity as a bar chart.
	"""
	try:
		image_data = await vs.trending_chart(hours, limit, format)
		
		# Return image response
		from fastapi.responses import StreamingResponse
		media_type = "image/svg+xml" if format == "svg" else "image/png"
		return StreamingResponse(
			io.BytesIO(image_data),
			media_type=media_type,
			headers={
				"Content-Disposition": f"inline; filename=trending_repos.{format}"
			}
		)
		
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/visualization/pr-timeline")
async def get_pr_timeline_chart(
	repo: str = Query(..., description="Repository name (e.g., 'owner/repo')"),
	days: int = Query(7, gt=0, le=30, description="Number of days to look back"),
	format: str = Query("png", pattern="^(png|svg)$", description="Image format"),
	vs: VisualizationServiceProtocol = Depends(get_visualization_service_dep),
):
	"""
	Generate a timeline visualization of pull request 'opened' events per day using VisualizationService.
	Returns an image (png/svg). 404 if no data in the given window.
	"""
	try:
		image_data = await vs.pr_timeline(repo, format)
		
		# Return image response
		from fastapi.responses import StreamingResponse
		media_type = "image/svg+xml" if format == "svg" else "image/png"
		return StreamingResponse(
			io.BytesIO(image_data),
			media_type=media_type,
			headers={"Content-Disposition": f"inline; filename=pr_timeline.{format}"}
		)
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/event-counts-timeseries", response_model=EventCountsTimeSeriesResponse)
async def get_event_counts_timeseries(
	hours: int = Query(24, gt=0, description="Number of hours to look back"),
	bucket_minutes: int = Query(5, gt=0, le=1440, description="Bucket size in minutes"),
	repo: Optional[str] = Query(None, description="Optional repository filter (owner/repo)"),
	ms: MetricsServiceProtocol = Depends(get_metrics_service_dep),
):
	"""Return bucketed event counts as JSON for charts or clients."""
	try:
		series = await ms.get_event_counts_timeseries(hours, bucket_minutes, repo)
		return EventCountsTimeSeriesResponse(
			hours=hours,
			bucket_minutes=bucket_minutes,
			repo=repo,
			series=[TimeSeriesPoint(**p) for p in series],
			timestamp=datetime.now(timezone.utc).isoformat(),
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

# Alias route to match README class diagram name (EventsTimeseriesEndpoint)
@app.get("/metrics/events-timeseries", response_model=EventCountsTimeSeriesResponse)
async def get_events_timeseries(
	hours: int = Query(24, gt=0, description="Number of hours to look back"),
	bucket_minutes: int = Query(5, gt=0, le=1440, description="Bucket size in minutes"),
	repo: Optional[str] = Query(None, description="Optional repository filter (owner/repo)"),
	ms: MetricsServiceProtocol = Depends(get_metrics_service_dep),
):
	"""Alias of event-counts-timeseries returning the same JSON payload."""
	return await get_event_counts_timeseries(hours=hours, bucket_minutes=bucket_minutes, repo=repo, ms=ms)

@app.get("/visualization/event-counts-timeseries")
async def get_event_counts_timeseries_chart(
	hours: int = Query(24, gt=0, description="Number of hours to look back"),
	bucket_minutes: int = Query(5, gt=0, le=1440, description="Bucket size in minutes"),
	repo: Optional[str] = Query(None, description="Optional repository filter (owner/repo)"),
	format: str = Query("png", pattern="^(png|svg)$", description="Image format"),
	vs: VisualizationServiceProtocol = Depends(get_visualization_service_dep),
):
	"""Generate an events timeseries chart for a repo or all repos."""
	try:
		image_data = await vs.events_timeseries_chart(hours, bucket_minutes, repo, format)
		from fastapi.responses import StreamingResponse
		media_type = "image/svg+xml" if format == "svg" else "image/png"
		return StreamingResponse(
			io.BytesIO(image_data),
			media_type=media_type,
			headers={
				"Content-Disposition": f"inline; filename=events_timeseries.{format}"
			}
		)
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


# ------------------------- Runtime Monitor Handlers --------------------------

@app.post("/monitors/start")
async def start_monitor(
	repository: str = Query(..., description="Repository (owner/repo) to monitor"),
	monitored_events: Optional[str] = Query(None, description="Comma-separated event types to monitor"),
	interval_seconds: int = Query(60, gt=0, le=3600, description="Polling interval in seconds"),
):
	"""Start a lightweight runtime monitor loop for a repository."""
	collector = await get_collector_instance()
	allowed = {"WatchEvent", "PullRequestEvent", "IssuesEvent"}
	selected = allowed
	if monitored_events:
		parts = {p.strip() for p in monitored_events.split(",") if p.strip()}
		selected = {p for p in parts if p in allowed} or allowed
	mon_id = collector.start_monitor(repository=repository, monitored_events=selected, interval_seconds=interval_seconds)
	return {"id": mon_id, "repository": repository, "monitored_events": sorted(list(selected)), "interval_seconds": interval_seconds}


@app.post("/monitors/{mon_id}/stop")
async def stop_monitor(mon_id: int):
	collector = await get_collector_instance()
	success = collector.stop_monitor(mon_id)
	if not success:
		raise HTTPException(status_code=404, detail="Monitor not found")
	return {"status": "stopped", "id": mon_id}


@app.get("/monitors")
async def get_active_monitors():
	collector = await get_collector_instance()
	return collector.get_active_monitors()


@app.get("/monitors/{mon_id}/events")
async def get_monitor_events(mon_id: int, limit: int = Query(100, gt=0, le=1000)):
	collector = await get_collector_instance()
	items = collector.get_events(mon_id, limit)
	if items is None:
		raise HTTPException(status_code=404, detail="Monitor not found")
	return items


@app.get("/monitors/{mon_id}/events/grouped")
async def get_monitor_events_grouped(mon_id: int):
	collector = await get_collector_instance()
	grouped = collector.get_events_grouped(mon_id)
	# Convert EventDict to plain dict of lists
	return grouped.to_dict()

# MCP capability discovery endpoints

def _get_doc(fn: Any) -> str:
	"""Safely get a trimmed docstring for a function"""
	doc = getattr(fn, "__doc__", None) or ""
	return " ".join(doc.strip().split()) if doc else ""

@app.get("/mcp/capabilities")
async def get_mcp_capabilities():
	"""List MCP tools, resources, and prompts exposed by the optional MCP server.

	If the MCP module is not available inside this package, return empty lists with a
	helpful note so clients can adapt gracefully.
	"""
	if not mcp_mod:
		return {
			"tools": [],
			"resources": [],
			"prompts": [],
			"note": "MCP server moved outside package; run scripts/mcp_server_cli.py to use MCP.",
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}
	tools = [
		{"name": "get_event_counts", "description": _get_doc(mcp_mod.get_event_counts)},
		{"name": "get_avg_pr_interval", "description": _get_doc(mcp_mod.get_avg_pr_interval)},
		{"name": "get_repository_activity", "description": _get_doc(mcp_mod.get_repository_activity)},
		{"name": "get_trending_repositories", "description": _get_doc(mcp_mod.get_trending_repositories)},
		{"name": "collect_events_now", "description": _get_doc(mcp_mod.collect_events_now)},
		{"name": "get_health", "description": _get_doc(mcp_mod.get_health)},
		{"name": "get_trending_chart_image", "description": _get_doc(getattr(mcp_mod, "get_trending_chart_image", None))},
		{"name": "get_pr_timeline_chart", "description": _get_doc(getattr(mcp_mod, "get_pr_timeline_chart", None))},
	]
	resources = [
		{"uri": "github://events/status", "name": "server_status", "description": _get_doc(mcp_mod.server_status)},
		{"uri": "github://events/recent/{event_type}", "name": "recent_events_by_type", "description": _get_doc(mcp_mod.recent_events_by_type)},
	]
	prompts = [
		{"name": "analyze_repository_trends", "description": _get_doc(mcp_mod.analyze_repository_trends)},
		{"name": "create_monitoring_dashboard_config", "description": _get_doc(mcp_mod.create_monitoring_dashboard_config)},
		{"name": "repository_health_assessment", "description": _get_doc(mcp_mod.repository_health_assessment)},
	]
	return {
		"tools": tools,
		"resources": resources,
		"prompts": prompts,
		"timestamp": datetime.now(timezone.utc).isoformat(),
	}

@app.get("/mcp/tools")
async def list_mcp_tools():
	return (await get_mcp_capabilities())["tools"]

@app.get("/mcp/resources")
async def list_mcp_resources():
	return (await get_mcp_capabilities())["resources"]

@app.get("/mcp/prompts")
async def list_mcp_prompts():
	return (await get_mcp_capabilities())["prompts"]

# Error handlers
@app.exception_handler(404)
async def not_found_handler(_request, exc):
	# Preserve explicit details from raised HTTPException when available
	detail = getattr(exc, "detail", None) or "Endpoint not found"
	return JSONResponse(
		status_code=404,
		content={"detail": detail}
	)

@app.exception_handler(500)
async def internal_error_handler(_request, exc):
	return JSONResponse(
		status_code=500,
		content={"detail": "Internal server error"}
	)

# Register endpoint classes to existing handlers now that all are defined
_register_endpoints_safely(app)


def run() -> None:
	"""Synchronous entry point to run the API server with uvicorn.

	Enables `uvx github-events-monitor-api` or installed console script usage.
	"""
	import uvicorn
	uvicorn.run(
		"github_events_monitor.api:app",
        host=API_HOST,
        port=API_PORT,
		reload=False,
		log_level="info",
	)

if __name__ == "__main__":
	run()


