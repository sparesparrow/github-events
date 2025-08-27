from __future__ import annotations
import os
from fastapi import FastAPI

from src.github_events_monitor.infrastructure.db_connection import DBConnection
from src.github_events_monitor.infrastructure.api_request_reader import ApiRequestReader
from src.github_events_monitor.infrastructure.api_response_writer import ApiResponseWriter
from src.github_events_monitor.infrastructure.events_repository import EventsRepository
from src.github_events_monitor.application.github_events_command_service import GitHubEventsCommandService
from src.github_events_monitor.application.github_events_query_service import GitHubEventsQueryService
from src.github_events_monitor.interfaces.api import endpoints

app = FastAPI(title="GitHub Events Monitor API", version="1.0.0")

# Singletons
_db = DBConnection(os.getenv("DATABASE_PATH", "./github_events.db"))
_reader = ApiRequestReader()
_writer = ApiResponseWriter(_db)
_repo = EventsRepository(_db)
_command_service = GitHubEventsCommandService(reader=_reader, writer=_writer)
_query_service = GitHubEventsQueryService(repository=_repo)


@app.on_event("startup")
async def _startup() -> None:
    await _db.initialize()


# Wire dependencies by overriding accessors
def _get_qs() -> GitHubEventsQueryService:
    return _query_service


def _get_cs() -> GitHubEventsCommandService:
    return _command_service


endpoints.get_query_service = _get_qs  # type: ignore
endpoints.get_command_service = _get_cs  # type: ignore

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
