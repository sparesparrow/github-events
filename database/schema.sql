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

-- Enhanced monitoring metrics tables
CREATE TABLE IF NOT EXISTS repository_health_metrics (
    repo_name TEXT PRIMARY KEY,
    health_score REAL,
    activity_score REAL,
    collaboration_score REAL,
    security_score REAL,
    total_events INTEGER DEFAULT 0,
    unique_contributors INTEGER DEFAULT 0,
    avg_issue_resolution_hours REAL,
    avg_pr_merge_hours REAL,
    deployment_frequency_per_week REAL,
    last_release_date TEXT,
    open_issues_count INTEGER DEFAULT 0,
    open_prs_count INTEGER DEFAULT 0,
    fork_count INTEGER DEFAULT 0,
    star_count INTEGER DEFAULT 0,
    last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_repo_health_score ON repository_health_metrics(health_score);
CREATE INDEX IF NOT EXISTS idx_repo_activity_score ON repository_health_metrics(activity_score);

-- Developer productivity metrics
CREATE TABLE IF NOT EXISTS developer_metrics (
    actor_login TEXT,
    repo_name TEXT,
    commits_count INTEGER DEFAULT 0,
    prs_opened INTEGER DEFAULT 0,
    prs_merged INTEGER DEFAULT 0,
    issues_opened INTEGER DEFAULT 0,
    issues_closed INTEGER DEFAULT 0,
    reviews_given INTEGER DEFAULT 0,
    comments_made INTEGER DEFAULT 0,
    productivity_score REAL,
    collaboration_score REAL,
    time_period TEXT, -- 'daily', 'weekly', 'monthly'
    period_start TEXT,
    period_end TEXT,
    last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (actor_login, repo_name, time_period, period_start)
);

CREATE INDEX IF NOT EXISTS idx_dev_productivity ON developer_metrics(productivity_score);
CREATE INDEX IF NOT EXISTS idx_dev_period ON developer_metrics(time_period, period_start);

-- Security and quality metrics
CREATE TABLE IF NOT EXISTS security_metrics (
    repo_name TEXT,
    metric_type TEXT, -- 'vulnerability', 'dependency_update', 'security_advisory', 'code_quality'
    severity TEXT,    -- 'low', 'medium', 'high', 'critical'
    count INTEGER DEFAULT 0,
    last_occurrence TEXT,
    resolved_count INTEGER DEFAULT 0,
    avg_resolution_hours REAL,
    date TEXT,
    last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (repo_name, metric_type, date)
);

CREATE INDEX IF NOT EXISTS idx_security_severity ON security_metrics(severity);
CREATE INDEX IF NOT EXISTS idx_security_type ON security_metrics(metric_type);

-- Event patterns and anomalies
CREATE TABLE IF NOT EXISTS event_patterns (
    repo_name TEXT,
    event_type TEXT,
    pattern_type TEXT, -- 'spike', 'drop', 'trend', 'anomaly'
    severity TEXT,     -- 'low', 'medium', 'high'
    description TEXT,
    threshold_value REAL,
    actual_value REAL,
    confidence_score REAL,
    detected_at TEXT,
    resolved_at TEXT,
    last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (repo_name, event_type, pattern_type, detected_at)
);

CREATE INDEX IF NOT EXISTS idx_patterns_severity ON event_patterns(severity);
CREATE INDEX IF NOT EXISTS idx_patterns_detected ON event_patterns(detected_at);

-- Release and deployment tracking
CREATE TABLE IF NOT EXISTS deployment_metrics (
    repo_name TEXT,
    deployment_id TEXT,
    environment TEXT,  -- 'production', 'staging', 'development'
    status TEXT,       -- 'pending', 'in_progress', 'success', 'failure', 'error'
    created_at TEXT,
    updated_at TEXT,
    duration_seconds INTEGER,
    commit_sha TEXT,
    tag_name TEXT,
    deployment_url TEXT,
    last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (repo_name, deployment_id)
);

CREATE INDEX IF NOT EXISTS idx_deployment_status ON deployment_metrics(status);
CREATE INDEX IF NOT EXISTS idx_deployment_env ON deployment_metrics(environment);
CREATE INDEX IF NOT EXISTS idx_deployment_created ON deployment_metrics(created_at);

-- Commit tracking and change monitoring
CREATE TABLE IF NOT EXISTS commits (
    sha TEXT PRIMARY KEY,
    repo_name TEXT NOT NULL,
    author_name TEXT,
    author_email TEXT,
    author_login TEXT,
    committer_name TEXT,
    committer_email TEXT,
    message TEXT,
    commit_date TEXT,
    push_event_id TEXT,
    branch_name TEXT,
    parent_shas TEXT, -- JSON array of parent commit SHAs
    stats_additions INTEGER DEFAULT 0,
    stats_deletions INTEGER DEFAULT 0,
    stats_total_changes INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    FOREIGN KEY (push_event_id) REFERENCES events(id)
);

CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repo_name);
CREATE INDEX IF NOT EXISTS idx_commits_author ON commits(author_login);
CREATE INDEX IF NOT EXISTS idx_commits_date ON commits(commit_date);
CREATE INDEX IF NOT EXISTS idx_commits_push_event ON commits(push_event_id);
CREATE INDEX IF NOT EXISTS idx_commits_branch ON commits(branch_name);

-- File changes tracking
CREATE TABLE IF NOT EXISTS commit_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_sha TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT, -- 'added', 'modified', 'removed', 'renamed'
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    changes INTEGER DEFAULT 0,
    patch TEXT, -- The actual diff patch
    previous_filename TEXT, -- For renamed files
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    FOREIGN KEY (commit_sha) REFERENCES commits(sha)
);

CREATE INDEX IF NOT EXISTS idx_commit_files_sha ON commit_files(commit_sha);
CREATE INDEX IF NOT EXISTS idx_commit_files_repo ON commit_files(repo_name);
CREATE INDEX IF NOT EXISTS idx_commit_files_filename ON commit_files(filename);
CREATE INDEX IF NOT EXISTS idx_commit_files_status ON commit_files(status);

-- Commit summaries and analysis
CREATE TABLE IF NOT EXISTS commit_summaries (
    commit_sha TEXT PRIMARY KEY,
    repo_name TEXT NOT NULL,
    summary_type TEXT, -- 'auto', 'ai', 'manual'
    short_summary TEXT,
    detailed_summary TEXT,
    change_categories TEXT, -- JSON array of change categories
    impact_score REAL, -- 0-100 score of commit impact
    risk_level TEXT, -- 'low', 'medium', 'high'
    breaking_changes BOOLEAN DEFAULT FALSE,
    security_relevant BOOLEAN DEFAULT FALSE,
    performance_impact TEXT, -- 'positive', 'negative', 'neutral', 'unknown'
    test_coverage_change REAL, -- Change in test coverage percentage
    complexity_score REAL, -- Code complexity score
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    FOREIGN KEY (commit_sha) REFERENCES commits(sha)
);

CREATE INDEX IF NOT EXISTS idx_commit_summaries_repo ON commit_summaries(repo_name);
CREATE INDEX IF NOT EXISTS idx_commit_summaries_impact ON commit_summaries(impact_score);
CREATE INDEX IF NOT EXISTS idx_commit_summaries_risk ON commit_summaries(risk_level);
CREATE INDEX IF NOT EXISTS idx_commit_summaries_breaking ON commit_summaries(breaking_changes);

-- Repository change tracking aggregates
CREATE TABLE IF NOT EXISTS repository_change_metrics (
    repo_name TEXT,
    date TEXT, -- YYYY-MM-DD format
    total_commits INTEGER DEFAULT 0,
    total_additions INTEGER DEFAULT 0,
    total_deletions INTEGER DEFAULT 0,
    total_files_changed INTEGER DEFAULT 0,
    unique_authors INTEGER DEFAULT 0,
    avg_commit_size REAL DEFAULT 0,
    breaking_changes_count INTEGER DEFAULT 0,
    security_commits_count INTEGER DEFAULT 0,
    high_impact_commits_count INTEGER DEFAULT 0,
    branches_active INTEGER DEFAULT 0,
    last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (repo_name, date)
);

CREATE INDEX IF NOT EXISTS idx_repo_changes_date ON repository_change_metrics(date);
CREATE INDEX IF NOT EXISTS idx_repo_changes_commits ON repository_change_metrics(total_commits);
CREATE INDEX IF NOT EXISTS idx_repo_changes_impact ON repository_change_metrics(high_impact_commits_count);
