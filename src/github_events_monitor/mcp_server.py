"""
GitHub Events Monitor - MCP Server

Model Context Protocol (MCP) server that exposes GitHub Events monitoring
functionality as MCP tools, resources, and prompts.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import httpx

from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent, ImageContent

"""Client configuration: talk to REST API instead of local collector"""
DATABASE_PATH = os.getenv("DATABASE_PATH", "github_events.db")  # For status display only
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))  # Unused in client mode
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
API_BASE_URL = os.getenv("API_BASE_URL", os.getenv("MCP_API_BASE_URL", "http://127.0.0.1:8001"))

# HTTP client state
http_client: Optional[httpx.AsyncClient] = None
last_health: Optional[Dict[str, Any]] = None

# Initialize MCP server
mcp = FastMCP(
	name="GitHub Events Monitor",
	dependencies=["httpx", "aiosqlite", "matplotlib"]
)

async def initialize_collector():
	"""Initialize HTTP client and verify API health (client mode)."""
	global http_client, last_health
	
	http_client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30)
	try:
		resp = await http_client.get("/health")
		resp.raise_for_status()
		last_health = resp.json()
	except Exception as e:
		# Keep running; tools will surface errors on demand
		last_health = {"status": "error", "message": str(e), "api_base_url": API_BASE_URL}

async def cleanup():
	"""Cleanup resources"""
	global http_client
	if http_client:
		await http_client.aclose()
		http_client = None

async def background_poller():
	"""Deprecated in client mode: no-op."""
	while False:
		await asyncio.sleep(POLL_INTERVAL)

# MCP Tools - Model-controlled functions

@mcp.tool()
async def get_event_counts(offset_minutes: int) -> Dict[str, Any]:
	"""
	Get the total number of events grouped by event type for a given time offset.
	
	Args:
		offset_minutes: Number of minutes to look back (must be positive)
	
	Returns:
		Dictionary containing event counts by type and metadata
	"""
	if not http_client:
		return {"error": "HTTP client not initialized"}
	try:
		if offset_minutes <= 0:
			return {"error": "offset_minutes must be positive"}
		resp = await http_client.get("/metrics/event-counts", params={"offset_minutes": offset_minutes})
		resp.raise_for_status()
		data = resp.json()
		# ensure schema
		return {
			"offset_minutes": data.get("offset_minutes", offset_minutes),
			"total_events": data.get("total_events", 0),
			"counts": data.get("counts", {}),
			"timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
			"success": True,
		}
	except Exception as e:
		return {"error": str(e), "success": False}

@mcp.tool()
async def get_avg_pr_interval(repo_name: str) -> Dict[str, Any]:
	"""
	Calculate the average time between pull request events for a given repository.
	
	Args:
		repo_name: Repository name in format 'owner/repo' (e.g., 'microsoft/vscode')
	
	Returns:
		Dictionary containing PR interval statistics or error information
	"""
	if not http_client:
		return {"error": "HTTP client not initialized"}
	try:
		resp = await http_client.get("/metrics/pr-interval", params={"repo": repo_name})
		resp.raise_for_status()
		result = resp.json() or {}
		# Normalize and enrich
		pr_count = int(result.get("pr_count", 0))
		avg_hours = result.get("avg_interval_hours") or 0
		result["success"] = True
		result["interpretation"] = {
			"frequency_description": _interpret_pr_frequency(avg_hours if isinstance(avg_hours, (int, float)) else 0),
			"activity_level": _interpret_activity_level(pr_count),
		}
		return result
	except Exception as e:
		return {"error": str(e), "success": False}

@mcp.tool()
async def get_repository_activity(repo_name: str, hours: int = 24) -> Dict[str, Any]:
	"""
	Get detailed activity summary for a specific repository.
	
	Args:
		repo_name: Repository name in format 'owner/repo'
		hours: Number of hours to look back (default: 24)
	
	Returns:
		Dictionary containing detailed repository activity information
	"""
	if not http_client:
		return {"error": "HTTP client not initialized"}
	try:
		resp = await http_client.get(
			"/metrics/repository-activity",
			params={"repo": repo_name, "hours": hours},
		)
		resp.raise_for_status()
		result = resp.json() or {}
		result["success"] = True
		total_events = result.get("total_events", 0) or 0
		result["insights"] = {
			"activity_rate_per_hour": (total_events / hours) if hours else 0,
			"most_common_event": _get_most_common_event(result.get("activity", {})),
			"activity_assessment": _assess_activity_level(int(total_events), int(hours or 1)),
		}
		return result
	except Exception as e:
		return {"error": str(e), "success": False}

@mcp.tool()
async def get_trending_repositories(hours: int = 24, limit: int = 10) -> Dict[str, Any]:
	"""
	Get most active repositories by event count.
	
	Args:
		hours: Number of hours to look back (default: 24)
		limit: Maximum number of repositories to return (default: 10)
	
	Returns:
		Dictionary containing trending repositories data
	"""
	if not http_client:
		return {"error": "HTTP client not initialized"}
	try:
		resp = await http_client.get("/metrics/trending", params={"hours": hours, "limit": limit})
		resp.raise_for_status()
		data = resp.json() or {}
		repos = data.get("repositories", [])
		return {
			"hours": data.get("hours", hours),
			"limit": limit,
			"repositories": repos,
			"total_found": len(repos),
			"timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
			"success": True,
		}
	except Exception as e:
		return {"error": str(e), "success": False}

@mcp.tool()
async def get_trending_chart_image(hours: int = 24, limit: int = 10, format: str = "png") -> Dict[str, Any]:
	"""
	Fetch the trending repositories chart image from the REST API.

	Args:
		hours: Number of hours to look back
		limit: Number of repositories to include
		format: Image format (png or svg)

	Returns:
		Dictionary with base64-encoded image data and media type
	"""
	if not http_client:
		return {"error": "HTTP client not initialized"}
	try:
		resp = await http_client.get(
			"/visualization/trending-chart",
			params={"hours": hours, "limit": limit, "format": format},
		)
		resp.raise_for_status()
		media_type = "image/svg+xml" if format == "svg" else "image/png"
		import base64 as _b64
		img_b64 = _b64.b64encode(resp.content).decode("utf-8")
		return {
			"success": True,
			"media_type": media_type,
			"format": format,
			"image_base64": img_b64,
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}
	except Exception as e:
		return {"error": str(e), "success": False}

@mcp.tool()
async def get_pr_timeline_chart(repo_name: str, days: int = 7, format: str = "png") -> Dict[str, Any]:
	"""
	Fetch PR timeline visualization or placeholder data from REST API.

	Args:
		repo_name: Repository name in format 'owner/repo'
		days: Number of days to look back
		format: Image format (png or svg)

	Returns:
		Dictionary with response from API (image or JSON placeholder for now)
	"""
	if not http_client:
		return {"error": "HTTP client not initialized"}
	try:
		resp = await http_client.get(
			"/visualization/pr-timeline",
			params={"repo": repo_name, "days": days, "format": format},
		)
		resp.raise_for_status()
		content_type = resp.headers.get("content-type", "application/json")
		if content_type.startswith("image/"):
			import base64 as _b64
			img_b64 = _b64.b64encode(resp.content).decode("utf-8")
			return {"success": True, "media_type": content_type, "image_base64": img_b64}
		else:
			return {"success": True, "data": resp.json()}
	except Exception as e:
		return {"error": str(e), "success": False}

@mcp.tool()
async def collect_events_now(limit: Optional[int] = None) -> Dict[str, Any]:
	"""
	Manually trigger immediate collection of events from GitHub API.
	
	Args:
		limit: Maximum number of events to collect (None for all available)
	
	Returns:
		Dictionary containing collection results
	"""
	if not http_client:
		return {"error": "HTTP client not initialized"}
	try:
		resp = await http_client.post("/collect", params=({"limit": limit} if limit is not None else {}))
		resp.raise_for_status()
		data = resp.json() or {}
		return {
			"message": data.get("message", "Collection started"),
			"limit": data.get("limit", limit),
			"timestamp": datetime.now(timezone.utc).isoformat(),
			"success": True,
		}
	except Exception as e:
		return {"error": str(e), "success": False}

@mcp.tool()
async def get_health() -> Dict[str, Any]:
	"""
	Get REST API health status and basic connectivity check.

	Returns:
		dict with service status and timestamp.
	"""
	if not http_client:
		return {"error": "HTTP client not initialized", "success": False}
	try:
		resp = await http_client.get("/health")
		resp.raise_for_status()
		data = resp.json()
		return {"success": True, "health": data}
	except Exception as e:
		return {"success": False, "error": str(e)}

# MCP Resources - Application-controlled data sources

@mcp.resource("github://events/status")
async def server_status() -> str:
	"""Return REST API health status for GitHub Events monitor."""
	if not http_client:
		return json.dumps({"status": "error", "message": "HTTP client not initialized"})
	try:
		resp = await http_client.get("/health")
		resp.raise_for_status()
		return json.dumps(resp.json(), indent=2)
	except Exception as e:
		return json.dumps({"status": "error", "message": str(e), "api_base_url": API_BASE_URL})

@mcp.resource("github://events/recent/{event_type}")
async def recent_events_by_type(event_type: str) -> str:
	"""
	Get recent events of a specific type
	
	Args:
		event_type: Type of events to retrieve (WatchEvent, PullRequestEvent, IssuesEvent)
	"""
	valid_types = {"WatchEvent", "PullRequestEvent", "IssuesEvent"}
	if event_type not in valid_types:
		return json.dumps({"error": f"Invalid event type. Must be one of: {sorted(valid_types)}"})
	try:
		# No direct REST endpoint yet; provide guidance
		result = {
			"event_type": event_type,
			"message": f"Recent {event_type} listing not available via REST API",
			"hint": "Consider adding /events/{event_type} endpoint to the API",
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}
		return json.dumps(result, indent=2)
	except Exception as e:
		return json.dumps({"error": str(e)})

# MCP Prompts - User-controlled templates

@mcp.prompt()
async def analyze_repository_trends(repo_name: str) -> str:
	"""
	Generate analysis prompt for repository activity trends.
	
	Args:
		repo_name: Repository name to analyze
	"""
	try:
		# Get current data for the prompt
		pr_data = await get_avg_pr_interval(repo_name)
		activity_data = await get_repository_activity(repo_name, 168)  # 1 week
		
		prompt = f"""Analyze the GitHub activity trends for repository: {repo_name}

Current Repository Metrics:
- Pull Request Frequency: {pr_data.get('pr_count', 0)} PRs tracked
- Average PR Interval: {pr_data.get('avg_interval_hours', 'N/A')} hours
- Recent Activity (7 days): {activity_data.get('total_events', 0)} total events

Activity Breakdown:"""
		
		for event_type, data in activity_data.get('activity', {}).items():
			prompt += f"\n- {event_type}: {data.get('count', 0)} events"
		
		prompt += """

Please provide insights on:
1. **Repository Health**: Is this repository actively maintained?
2. **Development Velocity**: How does the PR frequency compare to similar projects?
3. **Community Engagement**: What do the event patterns suggest about community involvement?
4. **Trends and Patterns**: Are there any notable trends in the activity data?
5. **Recommendations**: What actions could improve repository health and engagement?

Base your analysis on the GitHub event data provided above.
"""
		
		return prompt
		
	except Exception as e:
		return f"Error generating analysis prompt: {e}"

@mcp.prompt()
async def create_monitoring_dashboard_config(hours: int = 24) -> str:
	"""
	Generate configuration for monitoring dashboard setup.
	
	Args:
		hours: Time window for current metrics (default: 24 hours)
	"""
	try:
		# Get current trending data
		trending_data = await get_trending_repositories(hours, 10)
		
		prompt = f"""Create a monitoring dashboard configuration for GitHub Events tracking.

Current System Status (last {hours} hours):
- Active Repositories: {len(trending_data.get('repositories', []))}
- Top Repository: {trending_data.get('repositories', [{}])[0].get('repo_name', 'N/A') if trending_data.get('repositories') else 'N/A'}

Please design a comprehensive monitoring dashboard that includes:

1. **Key Metrics Panels**:
   - Real-time event counts by type
   - Top active repositories
   - Average PR intervals for key repositories
   - Event volume trends over time

2. **Alert Configurations**:
   - Thresholds for unusual activity spikes
   - Alerts for repositories with concerning PR patterns
   - System health monitoring alerts

3. **Visualization Requirements**:
   - Time series charts for event volumes
   - Bar charts for repository activity rankings
   - Heat maps for activity patterns
   - Trend indicators for velocity metrics

4. **Dashboard Layout**:
   - Primary metrics in top row
   - Detailed breakdowns in middle section
   - Historical trends at bottom
   - Alert status sidebar

5. **Refresh and Update Strategy**:
   - Real-time updates vs. scheduled refreshes
   - Data retention policies
   - Performance optimization techniques

Include specific recommendations for visualization libraries, data update frequencies, and user interaction features.
"""
		
		return prompt
		
	except Exception as e:
		return f"Error generating dashboard config prompt: {e}"

@mcp.prompt()
async def repository_health_assessment(repo_name: str) -> str:
	"""
	Generate prompt for comprehensive repository health assessment.
	
	Args:
		repo_name: Repository to assess
	"""
	try:
		# Gather comprehensive data
		pr_data = await get_avg_pr_interval(repo_name)
		activity_24h = await get_repository_activity(repo_name, 24)
		activity_7d = await get_repository_activity(repo_name, 168)
		
		prompt = f"""Conduct a comprehensive health assessment for GitHub repository: {repo_name}

## Repository Metrics Summary

**Pull Request Patterns:**
- Total PRs tracked: {pr_data.get('pr_count', 0)}
- Average interval between PRs: {pr_data.get('avg_interval_hours', 'N/A')} hours
- Median interval: {pr_data.get('median_interval_hours', 'N/A')} hours

**Recent Activity (24 hours):**
- Total events: {activity_24h.get('total_events', 0)}
- Activity rate: {activity_24h.get('insights', {}).get('activity_rate_per_hour', 0):.2f} events/hour

**Weekly Activity (7 days):**
- Total events: {activity_7d.get('total_events', 0)}
- Weekly activity rate: {activity_7d.get('total_events', 0) / 168:.2f} events/hour

## Assessment Framework

Please evaluate this repository across these dimensions:

1. **Development Velocity**
   - Is the PR frequency healthy for a project of this type?
   - Are there signs of development bottlenecks?
   - How consistent is the development activity?

2. **Community Engagement**
   - What do the watch events suggest about community interest?
   - Are issues being actively managed?
   - Is there evidence of contributor diversity?

3. **Project Sustainability**
   - Are there warning signs of maintainer burnout?
   - Is the project showing signs of healthy growth or decline?
   - How does recent activity compare to historical patterns?

4. **Operational Health**
   - Are PRs being merged at a reasonable pace?
   - Is there evidence of proper review processes?
   - Are issues being addressed promptly?

5. **Risk Factors**
   - Identify any concerning patterns in the data
   - Highlight potential sustainability risks
   - Note any anomalies that warrant investigation

Provide specific, actionable recommendations based on the data analysis.
"""
		
		return prompt
		
	except Exception as e:
		return f"Error generating health assessment prompt: {e}"

# Helper functions
def _interpret_pr_frequency(avg_hours: float) -> str:
	"""Interpret PR frequency in human terms"""
	if avg_hours <= 0:
		return "No data available"
	elif avg_hours < 1:
		return "Very high frequency (sub-hourly)"
	elif avg_hours < 24:
		return f"High frequency (~{avg_hours:.1f} hours between PRs)"
	elif avg_hours < 168:  # 1 week
		return f"Moderate frequency (~{avg_hours/24:.1f} days between PRs)"
	else:
		return f"Low frequency (~{avg_hours/168:.1f} weeks between PRs)"

def _interpret_activity_level(pr_count: int) -> str:
	"""Interpret activity level based on PR count"""
	if pr_count == 0:
		return "No PR activity detected"
	elif pr_count < 5:
		return "Low activity level"
	elif pr_count < 20:
		return "Moderate activity level"
	elif pr_count < 100:
		return "High activity level"
	else:
		return "Very high activity level"

def _get_most_common_event(activity: Dict[str, Any]) -> str:
	"""Get the most common event type from activity data"""
	if not activity:
		return "None"
	
	max_count = 0
	most_common = "None"
	
	for event_type, data in activity.items():
		count = data.get('count', 0)
		if count > max_count:
			max_count = count
			most_common = event_type
	
	return most_common

def _assess_activity_level(total_events: int, hours: int) -> str:
	"""Assess overall activity level"""
	rate = total_events / hours
	
	if rate == 0:
		return "Inactive"
	elif rate < 0.1:
		return "Very low activity"
	elif rate < 1:
		return "Low activity"
	elif rate < 5:
		return "Moderate activity"
	elif rate < 10:
		return "High activity"
	else:
		return "Very high activity"

# Server lifecycle management
async def main():
    """Main function to run the MCP server"""
    try:
        await initialize_collector()
        # Run the MCP server (avoid nested event loops by using the async stdio runner)
        if MCP_TRANSPORT.lower() != "stdio":
            raise ValueError(f"Unsupported MCP_TRANSPORT: {MCP_TRANSPORT}. Only 'stdio' is supported.")
        await mcp.run_stdio_async()
    finally:
        await cleanup()
if __name__ == "__main__":
	asyncio.run(main())

def run() -> None:
	"""Synchronous entry point for console_script.

	Allows running the MCP server via `uvx github-events-monitor-mcp` or
	installed console script without dealing with asyncio in entry point.
	"""
	asyncio.run(main())


