from __future__ import annotations
import json
from typing import Iterable

from src.github_events_monitor.domain.events import GitHubEvent
from src.github_events_monitor.domain.protocols import EventWriterProtocol
from src.github_events_monitor.infrastructure.db_connection import DBConnection


class ApiResponseWriter(EventWriterProtocol):
    def __init__(self, db: DBConnection) -> None:
        self.db = db

    async def store_events(self, events: Iterable[GitHubEvent]) -> int:
        # Idempotent insert (ignore duplicates by primary key)
        to_insert = list(events)
        if not to_insert:
            return 0
        async with self.db.connect() as conn:
            await conn.executemany(
                """
                INSERT OR IGNORE INTO events (id, event_type, repo_name, actor_login, created_at, created_at_ts, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.id,
                        e.event_type,
                        e.repo_name,
                        e.actor_login,
                        e.created_at.isoformat(),
                        int(e.created_at.timestamp()),
                        json.dumps(e.payload, ensure_ascii=False),
                    )
                    for e in to_insert
                ],
            )
            await conn.commit()
            # Count inserted by checking changes() is tricky across executemany; return len for simplicity
            return len(to_insert)
