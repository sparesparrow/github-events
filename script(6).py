# Create the FastAPI REST API module
fastapi_code = '''"""
GitHub Events Monitor - REST API

FastAPI application providing REST endpoints for GitHub Events monitoring metrics.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import io
import base64

from .collector import GitHubEventsCollector, get_collector

# Configuration from environment variables
DATABASE_PATH = os.getenv("DATABASE_PATH", "github_events.db")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))  # 5 minutes default

# Global collector instance
collector_instance: Optional[GitHubEventsCollector] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global collector_instance
    
    # Initialize collector
    collector_instance = GitHubEventsCollector(DATABASE_PATH, GITHUB_TOKEN)
    await collector_instance.initialize_database()
    
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
    """Dependency to get the collector instance"""
    if collector_instance is None:
        raise HTTPException(status_code=503, detail="Collector not initialized")
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
        
        await asyncio.sleep(POLL_INTERVAL)

# API Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        database_path=DATABASE_PATH,
        github_token_configured=bool(GITHUB_TOKEN),
        timestamp=datetime.now(timezone.utc).isoformat()
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

@app.get("/metrics/event-counts", response_model=EventCountsResponse)
async def get_event_counts(
    offset_minutes: int = Query(..., gt=0, description="Number of minutes to look back"),
    collector: GitHubEventsCollector = Depends(get_collector_instance)
):
    """
    Get total number of events grouped by event type for a given offset.
    
    The offset determines how much time we want to look back.
    For example, offset_minutes=10 means count events from the last 10 minutes.
    """
    try:
        counts = await collector.get_event_counts_by_type(offset_minutes)
        total_events = sum(counts.values())
        
        return EventCountsResponse(
            offset_minutes=offset_minutes,
            total_events=total_events,
            counts=counts,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/pr-interval", response_model=PRIntervalResponse)
async def get_pr_interval(
    repo: str = Query(..., description="Repository name (e.g., 'owner/repo')"),
    collector: GitHubEventsCollector = Depends(get_collector_instance)
):
    """
    Calculate the average time between pull requests for a given repository.
    
    Only considers PR 'opened' events for meaningful interval calculation.
    """
    try:
        result = await collector.get_avg_pr_interval(repo)
        
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
    hours: int = Query(24, gt=0, description="Number of hours to look back"),
    collector: GitHubEventsCollector = Depends(get_collector_instance)
):
    """Get detailed activity summary for a specific repository"""
    try:
        result = await collector.get_repository_activity_summary(repo, hours)
        return RepositoryActivityResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/trending", response_model=TrendingRepositoriesResponse)
async def get_trending_repositories(
    hours: int = Query(24, gt=0, description="Number of hours to look back"),
    limit: int = Query(10, gt=0, le=50, description="Maximum number of repositories to return"),
    collector: GitHubEventsCollector = Depends(get_collector_instance)
):
    """Get most active repositories by event count"""
    try:
        trending_data = await collector.get_trending_repositories(hours, limit)
        
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
    format: str = Query("png", regex="^(png|svg)$", description="Image format"),
    collector: GitHubEventsCollector = Depends(get_collector_instance)
):
    """
    Generate a visualization chart of trending repositories.
    
    This is the bonus visualization endpoint showing repository activity as a bar chart.
    """
    try:
        trending_data = await collector.get_trending_repositories(hours, limit)
        
        if not trending_data:
            raise HTTPException(status_code=404, detail="No data found for the specified time period")
        
        # Extract data for plotting
        repo_names = [repo['repo_name'].split('/')[-1][:20] for repo in trending_data]  # Short names
        event_counts = [repo['total_events'] for repo in trending_data]
        
        # Create the chart
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        bars = ax.barh(range(len(repo_names)), event_counts, color='steelblue', alpha=0.7)
        
        # Customize the chart
        ax.set_yticks(range(len(repo_names)))
        ax.set_yticklabels(repo_names)
        ax.set_xlabel('Number of Events')
        ax.set_title(f'Most Active GitHub Repositories (Last {hours} Hours)')
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
            media_type = "image/svg+xml"
        else:
            plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
            media_type = "image/png"
        
        plt.close()
        
        img_buffer.seek(0)
        
        # Return image response
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(img_buffer.read()),
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename=trending_repos.{format}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/visualization/pr-timeline")
async def get_pr_timeline_chart(
    repo: str = Query(..., description="Repository name (e.g., 'owner/repo')"),
    days: int = Query(7, gt=0, le=30, description="Number of days to look back"),
    format: str = Query("png", regex="^(png|svg)$", description="Image format"),
    collector: GitHubEventsCollector = Depends(get_collector_instance)
):
    """
    Generate a timeline visualization of pull request activity for a repository.
    
    Additional bonus visualization showing PR activity over time.
    """
    try:
        # This would require extending the collector to get time-series data
        # For now, return a simple message
        return {"message": "PR timeline visualization endpoint", "repo": repo, "days": days}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
'''

# Save the FastAPI module
with open("github_events_monitor/api.py", "w") as f:
    f.write(fastapi_code)

print("✅ Created github_events_monitor/api.py")
print(f"📊 Size: {len(fastapi_code)} characters")
print("\nFastAPI REST API features:")
print("- /health - Health check endpoint")
print("- /collect - Manual event collection trigger")  
print("- /metrics/event-counts - Get event counts by type with time offset")
print("- /metrics/pr-interval - Calculate average time between PRs")
print("- /metrics/repository-activity - Get repository activity summary")
print("- /metrics/trending - Get most active repositories")
print("- /visualization/trending-chart - Generate trending repositories chart (BONUS)")
print("- Background polling task for continuous event collection")
print("- Comprehensive error handling and response models")