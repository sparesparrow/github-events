"""
GitHub Events Monitor - API Endpoints Abstraction

This module defines a base `ApiEndpoint` class and concrete endpoint classes
for each implemented REST API endpoint. These classes encapsulate the route
metadata and provide a `register()` method to attach the endpoint to a FastAPI
application or router without modifying existing function-based routes.

Usage pattern (optional integration):

    from fastapi import FastAPI
    from .api_endpoints import HealthEndpoint

    app = FastAPI()
    health = HealthEndpoint(handler=my_health_handler)
    health.register(app)

The concrete endpoint classes accept handler callables that implement the
actual business logic. This keeps the abstraction decoupled from the current
implementation and avoids circular imports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, Optional, Union, List

from fastapi import APIRouter, FastAPI

HttpHandler = Callable[..., Awaitable[Any]]
RouteTarget = Union[FastAPI, APIRouter]


class ApiEndpoint(ABC):
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
	
	@abstractmethod
	def get_handler(self) -> HttpHandler:
		"""Return the async handler callable for this endpoint."""
		...
	
	def register(self, target: RouteTarget) -> None:
		"""Register this endpoint on the provided FastAPI app or APIRouter."""
		target.add_api_route(
			self.path,
			self.get_handler(),
			methods=[self.method],
			name=self.name,
			summary=self.summary,
		)


# ------------------------------- Health ------------------------------------

class HealthEndpoint(ApiEndpoint):
	"""GET /health"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/health",
			method="GET",
			name="health_check",
			summary="Service health check",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured() -> Dict[str, Any]:
				return {"error": "Health handler not configured"}
			return _not_configured
		return self._handler


# ------------------------------ Collection ---------------------------------

class CollectEndpoint(ApiEndpoint):
	"""POST /collect"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/collect",
			method="POST",
			name="manual_collect",
			summary="Manually trigger event collection",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured(limit: Optional[int] = None) -> Dict[str, Any]:
				return {"error": "Collect handler not configured", "limit": limit}
			return _not_configured
		return self._handler


class WebhookEndpoint(ApiEndpoint):
	"""POST /webhook"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/webhook",
			method="POST",
			name="github_webhook",
			summary="Optional GitHub webhook receiver",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
				return {"status": "ignored", "reason": "Webhook handler not configured"}
			return _not_configured
		return self._handler


# ------------------------------- Metrics -----------------------------------

class MetricsEventCountsEndpoint(ApiEndpoint):
	"""GET /metrics/event-counts"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/event-counts",
			method="GET",
			name="get_event_counts",
			summary="Get event counts by type",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured(offset_minutes: int) -> Dict[str, Any]:
				return {"error": "MetricsEventCounts handler not configured", "offset_minutes": offset_minutes}
			return _not_configured
		return self._handler


class MetricsPrIntervalEndpoint(ApiEndpoint):
	"""GET /metrics/pr-interval"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/pr-interval",
			method="GET",
			name="get_pr_interval",
			summary="Get average PR interval for a repository",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured(repo: str) -> Dict[str, Any]:
				return {"error": "MetricsPrInterval handler not configured", "repo": repo}
			return _not_configured
		return self._handler


class MetricsRepositoryActivityEndpoint(ApiEndpoint):
	"""GET /metrics/repository-activity"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/repository-activity",
			method="GET",
			name="get_repository_activity",
			summary="Get activity summary for a repository",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured(repo: str, hours: int = 24) -> Dict[str, Any]:
				return {"error": "MetricsRepositoryActivity handler not configured", "repo": repo, "hours": hours}
			return _not_configured
		return self._handler


class MetricsTrendingEndpoint(ApiEndpoint):
	"""GET /metrics/trending"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/metrics/trending",
			method="GET",
			name="get_trending_repositories",
			summary="Get trending repositories by event count",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured(hours: int = 24, limit: int = 10) -> Dict[str, Any]:
				return {"error": "MetricsTrending handler not configured", "hours": hours, "limit": limit}
			return _not_configured
		return self._handler


# ---------------------------- Visualization --------------------------------

class VisualizationTrendingChartEndpoint(ApiEndpoint):
	"""GET /visualization/trending-chart"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/visualization/trending-chart",
			method="GET",
			name="get_trending_chart",
			summary="Generate trending repositories chart",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured(hours: int = 24, limit: int = 10, format: str = "png") -> Dict[str, Any]:
				return {"error": "VisualizationTrendingChart handler not configured", "hours": hours, "limit": limit, "format": format}
			return _not_configured
		return self._handler


class VisualizationPrTimelineEndpoint(ApiEndpoint):
	"""GET /visualization/pr-timeline"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/visualization/pr-timeline",
			method="GET",
			name="get_pr_timeline_chart",
			summary="Generate PR timeline chart for a repository",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured(repo: str, days: int = 7, format: str = "png") -> Dict[str, Any]:
				return {"error": "VisualizationPrTimeline handler not configured", "repo": repo, "days": days, "format": format}
			return _not_configured
		return self._handler


# ------------------------------- MCP meta ----------------------------------

class McpCapabilitiesEndpoint(ApiEndpoint):
	"""GET /mcp/capabilities"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/mcp/capabilities",
			method="GET",
			name="get_mcp_capabilities",
			summary="List MCP tools, resources, and prompts",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured() -> Dict[str, Any]:
				return {"error": "MCP capabilities handler not configured"}
			return _not_configured
		return self._handler


class McpToolsEndpoint(ApiEndpoint):
	"""GET /mcp/tools"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/mcp/tools",
			method="GET",
			name="list_mcp_tools",
			summary="List MCP tools",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured() -> Dict[str, Any]:
				return {"error": "MCP tools handler not configured"}
			return _not_configured
		return self._handler


class McpResourcesEndpoint(ApiEndpoint):
	"""GET /mcp/resources"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/mcp/resources",
			method="GET",
			name="list_mcp_resources",
			summary="List MCP resources",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured() -> Dict[str, Any]:
				return {"error": "MCP resources handler not configured"}
			return _not_configured
		return self._handler


class McpPromptsEndpoint(ApiEndpoint):
	"""GET /mcp/prompts"""
	def __init__(self, handler: Optional[HttpHandler] = None) -> None:
		super().__init__(
			path="/mcp/prompts",
			method="GET",
			name="list_mcp_prompts",
			summary="List MCP prompts",
			handler=handler,
		)
	
	def get_handler(self) -> HttpHandler:
		if self._handler is None:
			async def _not_configured() -> Dict[str, Any]:
				return {"error": "MCP prompts handler not configured"}
			return _not_configured
		return self._handler


# -------------------------- Helper to build router --------------------------

def build_api_router(endpoints: Optional[List[ApiEndpoint]] = None) -> APIRouter:
	"""Build an APIRouter from a list of endpoint objects.
	
	This is a convenience for optional integration, allowing the caller to
	instantiate endpoint classes with appropriate handlers and register them
	onto a router in one place.
	"""
	router = APIRouter()
	if endpoints:
		for ep in endpoints:
			ep.register(router)
	return router
