-- GitHub Events MCP Server Database Schema

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create events table with proper indexing
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    gh_id TEXT UNIQUE NOT NULL,
    repo_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    payload JSONB,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_repo_created 
    ON events (repo_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_type_created 
    ON events (event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_created_at 
    ON events (created_at DESC);

-- Create aggregates table for fast metric queries
CREATE TABLE IF NOT EXISTS event_aggregates (
    id BIGSERIAL PRIMARY KEY,
    repo_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    minute_bucket TIMESTAMPTZ NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repo_name, event_type, minute_bucket)
);

-- Index for aggregates table
CREATE INDEX IF NOT EXISTS idx_aggregates_repo_type_minute 
    ON event_aggregates (repo_name, event_type, minute_bucket DESC);

-- Create a view for recent activity summary
CREATE OR REPLACE VIEW recent_activity AS
SELECT 
    repo_name,
    event_type,
    COUNT(*) as event_count,
    MIN(created_at) as first_event,
    MAX(created_at) as last_event,
    MAX(created_at) - MIN(created_at) as time_span
FROM events 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY repo_name, event_type
ORDER BY event_count DESC;

-- Create function to calculate PR intervals
CREATE OR REPLACE FUNCTION calculate_pr_interval(repo_name_param TEXT)
RETURNS TABLE(
    pr_count BIGINT,
    avg_interval_seconds NUMERIC,
    median_interval_seconds NUMERIC,
    stddev_interval_seconds NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH pr_events AS (
        SELECT 
            created_at,
            LAG(created_at) OVER (ORDER BY created_at) as prev_created_at
        FROM events 
        WHERE repo_name = repo_name_param 
          AND event_type = 'PullRequestEvent'
          AND payload->>'action' = 'opened'
        ORDER BY created_at
    ),
    intervals AS (
        SELECT EXTRACT(EPOCH FROM (created_at - prev_created_at)) as interval_seconds
        FROM pr_events 
        WHERE prev_created_at IS NOT NULL
    )
    SELECT 
        (SELECT COUNT(*) FROM pr_events)::BIGINT as pr_count,
        AVG(interval_seconds)::NUMERIC as avg_interval_seconds,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY interval_seconds)::NUMERIC as median_interval_seconds,
        STDDEV(interval_seconds)::NUMERIC as stddev_interval_seconds
    FROM intervals;
END;
$$ LANGUAGE plpgsql;

-- Insert sample data for testing (optional)
-- This would typically be populated by the MCP server
