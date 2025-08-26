"""
GitHub Events Monitor - REST API

FastAPI application providing REST endpoints for GitHub Events monitoring metrics.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import JSONResponse
from fastapi import Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import io

from .collector import GitHubEventsCollector
from .services import MetricsService, VisualizationService, EventsRepository, HealthReporter
from pathlib import Path
from . import mcp_server as mcp_mod
from .api_endpoints import (
	ApiEndpoint,
	HealthEndpoint,
	CollectEndpoint,
	WebhookEndpoint,
	MetricsEventCountsEndpoint,
	MetricsPrIntervalEndpoint,
	MetricsRepositoryActivityEndpoint,
	MetricsTrendingEndpoint,
	VisualizationTrendingChartEndpoint,
	VisualizationPrTimelineEndpoint,
	McpCapabilitiesEndpoint,
	McpToolsEndpoint,
	McpResourcesEndpoint,
	McpPromptsEndpoint,
)


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
	endpoint_objects = [
		HealthEndpoint(handler=health_check),
		CollectEndpoint(handler=manual_collect),
		WebhookEndpoint(handler=github_webhook),
		MetricsEventCountsEndpoint(handler=get_event_counts),
		MetricsPrIntervalEndpoint(handler=get_pr_interval),
		MetricsRepositoryActivityEndpoint(handler=get_repository_activity),
		MetricsTrendingEndpoint(handler=get_trending_repositories),
		VisualizationTrendingChartEndpoint(handler=get_trending_chart),
		VisualizationPrTimelineEndpoint(handler=get_pr_timeline_chart),
		McpCapabilitiesEndpoint(handler=get_mcp_capabilities),
		McpToolsEndpoint(handler=list_mcp_tools),
		McpResourcesEndpoint(handler=list_mcp_resources),
		McpPromptsEndpoint(handler=list_mcp_prompts),
	]
	for ep in endpoint_objects:
		if not _route_exists(app, ep.path, ep.method):
			ep.register(app)


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
async def health_check():
	"""Health check endpoint handler (registered via HealthEndpoint class)"""
	if health_reporter is None:
		raise HTTPException(status_code=503, detail="Health reporter not initialized")
	
	status_data = await health_reporter.status()
	
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
		from .collector import GitHubEvent
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
	offset_minutes: int = Query(..., gt=0, description="Number of minutes to look back")
):
	"""
	Get total number of events grouped by event type for a given offset using MetricsService.
	
	The offset determines how much time we want to look back.
	For example, offset_minutes=10 means count events from the last 10 minutes.
	"""
	if metrics_service is None:
		raise HTTPException(status_code=503, detail="Metrics service not initialized")
	
	try:
		result = await metrics_service.get_event_counts(offset_minutes)
		return EventCountsResponse(**result)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/pr-interval", response_model=PRIntervalResponse)
async def get_pr_interval(
	repo: str = Query(..., description="Repository name (e.g., 'owner/repo')")
):
	"""
	Calculate the average time between pull requests for a given repository using MetricsService.
	
	Only considers PR 'opened' events for meaningful interval calculation.
	"""
	if metrics_service is None:
		raise HTTPException(status_code=503, detail="Metrics service not initialized")
	
	try:
		result = await metrics_service.get_pr_interval(repo)
		
		if result is None:
			return PRIntervalResponse(
				repo_name=repo,
				pr_count=0
			)
		
		return PRIntervalResponse(**result)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/repository-activity", response_model=RepositoryActivityResponse)
async def get_repository_activity(
	repo: str = Query(..., description="Repository name (e.g., 'owner/repo')"),
	hours: int = Query(24, gt=0, description="Number of hours to look back")
):
	"""Get detailed activity summary for a specific repository using MetricsService"""
	if metrics_service is None:
		raise HTTPException(status_code=503, detail="Metrics service not initialized")
	
	try:
		result = await metrics_service.get_repository_activity(repo, hours)
		return RepositoryActivityResponse(**result)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/trending", response_model=TrendingRepositoriesResponse)
async def get_trending_repositories(
	hours: int = Query(24, gt=0, description="Number of hours to look back"),
	limit: int = Query(10, gt=0, le=50, description="Maximum number of repositories to return")
):
	"""Get most active repositories by event count using MetricsService"""
	if metrics_service is None:
		raise HTTPException(status_code=503, detail="Metrics service not initialized")
	
	try:
		trending_data = await metrics_service.get_trending(hours, limit)
		
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
	format: str = Query("png", pattern="^(png|svg)$", description="Image format")
):
	"""
	Generate a visualization chart of trending repositories using VisualizationService.
	
	This is the bonus visualization endpoint showing repository activity as a bar chart.
	"""
	if visualization_service is None:
		raise HTTPException(status_code=503, detail="Visualization service not initialized")
	
	try:
		image_data = await visualization_service.trending_chart(hours, limit, format)
		
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
    format: str = Query("png", pattern="^(png|svg)$", description="Image format")
):
	"""
	Generate a timeline visualization of pull request 'opened' events per day using VisualizationService.
	Returns an image (png/svg). 404 if no data in the given window.
	"""
	if visualization_service is None:
		raise HTTPException(status_code=503, detail="Visualization service not initialized")
	
	try:
		image_data = await visualization_service.pr_timeline(repo, format)
		
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

# MCP capability discovery endpoints

def _get_doc(fn: Any) -> str:
	"""Safely get a trimmed docstring for a function"""
	doc = getattr(fn, "__doc__", None) or ""
	return " ".join(doc.strip().split()) if doc else ""

@app.get("/mcp/capabilities")
async def get_mcp_capabilities():
	"""List MCP tools, resources, and prompts exposed by the server"""
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


