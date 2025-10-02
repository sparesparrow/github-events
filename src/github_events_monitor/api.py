from __future__ import annotations
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.github_events_monitor.infrastructure.db_connection import DBConnection
from src.github_events_monitor.infrastructure.api_request_reader import ApiRequestReader
from src.github_events_monitor.infrastructure.api_response_writer import ApiResponseWriter
from src.github_events_monitor.infrastructure.events_repository import EventsRepository
from src.github_events_monitor.application.github_events_command_service import GitHubEventsCommandService
from src.github_events_monitor.application.github_events_query_service import GitHubEventsQueryService
from src.github_events_monitor.interfaces.api import endpoints

# Singletons
_db = DBConnection(os.getenv("DATABASE_PATH", "./github_events.db"))
_reader = ApiRequestReader()
_writer = ApiResponseWriter(_db)
_repo = EventsRepository(_db)
_command_service = GitHubEventsCommandService(reader=_reader, writer=_writer)
_query_service = GitHubEventsQueryService(repository=_repo)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup/shutdown events.
    Replaces deprecated @app.on_event decorators.
    """
    # Startup
    await _db.initialize()
    yield
    # Shutdown (currently no cleanup needed)


app = FastAPI(
    title="GitHub Events Monitor API",
    version="1.2.3",
    description="Monitor GitHub events with comprehensive analytics and metrics",
    lifespan=lifespan
)

# Wire dependencies by setting the singleton instances
endpoints._query_service_instance = _query_service  # type: ignore
endpoints._command_service_instance = _command_service  # type: ignore

# Include routes
app.include_router(endpoints.router)

if __name__ == "__main__":
    # For local dev: python -m src.github_events_monitor.api
    import uvicorn

    uvicorn.run(app, host=os.getenv("API_HOST", "0.0.0.0"), port=int(os.getenv("API_PORT", "8000")))

def run() -> None:
    import uvicorn
    uvicorn.run(
        "github_events_monitor.api:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
    )
