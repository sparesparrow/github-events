-- Canonical schema aligned with src.github_events_monitor.collector
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    actor_login TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    payload TEXT NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_repo_name ON events(repo_name);
CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_repo_type_created ON events(repo_name, event_type, created_at);

-- Optional metrics table (unused by runtime but kept for compatibility)
CREATE TABLE IF NOT EXISTS pr_metrics (
    repo_name TEXT PRIMARY KEY,
    avg_time_between_prs_minutes REAL,
    total_prs INTEGER,
    last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
