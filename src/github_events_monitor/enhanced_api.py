"""
Enhanced API with database abstraction support.

This API can work with both SQLite and DynamoDB backends seamlessly,
using the abstract database interface.
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from .infrastructure.database_service import DatabaseService, initialize_database_service
from .infrastructure.database_factory import create_database_manager_from_config
from .enhanced_event_collector import EnhancedGitHubEventsCollector
from .config import config

logger = logging.getLogger(__name__)


# Global instances
_database_service: DatabaseService = None
_enhanced_collector: EnhancedGitHubEventsCollector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global _database_service, _enhanced_collector
    
    try:
        # Initialize database service
        logger.info(f"Initializing database service with provider: {config.database_provider}")
        _database_service = await initialize_database_service()
        
        # Initialize enhanced collector
        _enhanced_collector = EnhancedGitHubEventsCollector(
            database_service=_database_service,
            github_token=config.github_token,
            target_repositories=config.target_repositories
        )
        await _enhanced_collector.initialize()
        
        logger.info("Enhanced API initialized successfully")
        yield
        
    finally:
        # Cleanup
        if _enhanced_collector:
            await _enhanced_collector.close()
        if _database_service:
            await _database_service.close()
        logger.info("Enhanced API shutdown completed")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="GitHub Events Monitor Enhanced API",
    version="2.0.0",
    description="Enhanced GitHub Events Monitor with database abstraction support",
    lifespan=lifespan
)


def get_database_service() -> DatabaseService:
    """Get database service instance."""
    if _database_service is None:
        raise HTTPException(status_code=500, detail="Database service not initialized")
    return _database_service


def get_enhanced_collector() -> EnhancedGitHubEventsCollector:
    """Get enhanced collector instance."""
    if _enhanced_collector is None:
        raise HTTPException(status_code=500, detail="Enhanced collector not initialized")
    return _enhanced_collector


@app.get("/health")
async def health():
    """Enhanced health check with database provider information."""
    try:
        collector = get_enhanced_collector()
        health_data = await collector.health_check()
        return health_data
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_provider": config.database_provider
        }


@app.get("/database/info")
async def database_info():
    """Get detailed database information."""
    try:
        db_service = get_database_service()
        health = await db_service.health_check()
        
        return {
            "provider": config.database_provider,
            "configuration": {
                "database_path": config.database_path if config.database_provider == "sqlite" else None,
                "aws_region": config.aws_region if config.database_provider == "dynamodb" else None,
                "table_prefix": config.dynamodb_table_prefix if config.database_provider == "dynamodb" else None,
                "endpoint_url": config.dynamodb_endpoint_url if config.database_provider == "dynamodb" else None
            },
            "health": health
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database info error: {str(e)}")


# Enhanced endpoints using the new collector
@app.get("/enhanced/commits/recent")
async def enhanced_commits_recent(
    repo: str,
    hours: int = 24,
    limit: int = 50
):
    """Get recent commits using enhanced collector."""
    try:
        collector = get_enhanced_collector()
        commits = await collector.get_recent_commits(repo, hours, limit)
        
        return {
            "repo": repo,
            "hours": hours,
            "limit": limit,
            "total_commits": len(commits),
            "commits": commits,
            "database_provider": config.database_provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent commits: {str(e)}")


@app.get("/enhanced/repository/change-summary")
async def enhanced_repository_change_summary(
    repo: str,
    hours: int = 24
):
    """Get repository change summary using enhanced collector."""
    try:
        collector = get_enhanced_collector()
        summary = await collector.get_repository_change_summary(repo, hours)
        summary["database_provider"] = config.database_provider
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get change summary: {str(e)}")


@app.get("/enhanced/events/counts")
async def enhanced_event_counts(
    hours: int = 1,
    repo: str = None
):
    """Get event counts using enhanced collector."""
    try:
        collector = get_enhanced_collector()
        counts = await collector.get_event_counts_by_type(hours_back=hours)
        
        return {
            "hours": hours,
            "repo": repo,
            "counts": counts,
            "total_events": sum(counts.values()),
            "database_provider": config.database_provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get event counts: {str(e)}")


@app.get("/enhanced/trending")
async def enhanced_trending(
    hours: int = 24,
    limit: int = 10
):
    """Get trending repositories using enhanced collector."""
    try:
        collector = get_enhanced_collector()
        trending = await collector.get_trending_repositories(hours_back=hours, limit=limit)
        
        return {
            "hours": hours,
            "limit": limit,
            "repositories": trending,
            "database_provider": config.database_provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trending repositories: {str(e)}")


@app.post("/enhanced/collect")
async def enhanced_collect(
    limit: int = 100
):
    """Collect events using enhanced collector."""
    try:
        collector = get_enhanced_collector()
        stored_count = await collector.fetch_and_store_events(limit=limit)
        
        return {
            "status": "success",
            "events_stored": stored_count,
            "limit": limit,
            "database_provider": config.database_provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to collect events: {str(e)}")


@app.get("/enhanced/database/switch")
async def enhanced_database_switch_info():
    """Get information about database provider switching."""
    return {
        "current_provider": config.database_provider,
        "supported_providers": ["sqlite", "dynamodb"],
        "configuration": {
            "sqlite": {
                "description": "Local SQLite database file",
                "use_case": "Development, small deployments, single instance",
                "setup": "Set DATABASE_PROVIDER=sqlite and DATABASE_PATH"
            },
            "dynamodb": {
                "description": "AWS DynamoDB managed service",
                "use_case": "Production, scalable deployments, multi-instance",
                "setup": "Set DATABASE_PROVIDER=dynamodb and AWS configuration"
            }
        },
        "switching_instructions": {
            "to_sqlite": [
                "Set DATABASE_PROVIDER=sqlite",
                "Set DATABASE_PATH=./github_events.db",
                "Restart application"
            ],
            "to_dynamodb": [
                "Set DATABASE_PROVIDER=dynamodb",
                "Configure AWS credentials and region",
                "Run: python scripts/setup_dynamodb.py create",
                "Restart application"
            ]
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level=config.log_level.lower()
    )