CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    actor_id INTEGER,
    actor_login TEXT,
    repo_id INTEGER,
    repo_name TEXT,
    created_at TEXT,           -- ISO8601 string from GitHub (UTC)
    created_at_ts INTEGER,     -- Unix epoch seconds (UTC)
    payload TEXT,
    processed_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_repo_name ON events(repo_name);
CREATE INDEX IF NOT EXISTS idx_events_created_ts ON events(created_at_ts);

CREATE TABLE IF NOT EXISTS pr_metrics (
    repo_name TEXT PRIMARY KEY,
    avg_time_between_prs_minutes REAL,
    total_prs INTEGER,
    last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
