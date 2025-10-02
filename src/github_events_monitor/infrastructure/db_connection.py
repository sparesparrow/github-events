from __future__ import annotations
import os
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncIterator


class DBConnection:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("DATABASE_PATH", "./github_events.db")

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    repo_name TEXT,
                    actor_login TEXT,
                    created_at TEXT NOT NULL,
                    created_at_ts INTEGER NOT NULL,
                    payload TEXT
                )
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_events_created_at_ts ON events(created_at_ts)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_events_repo ON events(repo_name)")
            await db.commit()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        async with aiosqlite.connect(self.db_path) as conn:
            yield conn
