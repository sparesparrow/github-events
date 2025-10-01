"""
SQLite adapter implementation following the database interface.

This module provides SQLite implementations of the abstract database interfaces,
maintaining compatibility with the existing SQLite-based system.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

import aiosqlite

from .database_interface import (
    DatabaseConnection, EventsRepository, CommitsRepository, 
    MetricsRepository, DatabaseManager, EventData, CommitData, MetricsData
)

logger = logging.getLogger(__name__)


class SQLiteConnection(DatabaseConnection):
    """SQLite connection implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get('db_path', 'github_events.db')
        self.schema_path = config.get('schema_path', 'database/schema.sql')
        
        # Ensure directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Initialize SQLite database and create tables."""
        await self._create_tables()
    
    async def _create_tables(self) -> None:
        """Create tables from schema file."""
        try:
            # Read schema file
            schema_content = ""
            if Path(self.schema_path).exists():
                with open(self.schema_path, 'r') as f:
                    schema_content = f.read()
            else:
                # Fallback to embedded schema
                schema_content = self._get_embedded_schema()
            
            # Execute schema
            async with aiosqlite.connect(self.db_path) as db:
                await db.executescript(schema_content)
                await db.commit()
                
            logger.info(f"SQLite database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise
    
    def _get_embedded_schema(self) -> str:
        """Get embedded schema as fallback."""
        return """
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

        -- Commit tracking tables
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
            parent_shas TEXT,
            stats_additions INTEGER DEFAULT 0,
            stats_deletions INTEGER DEFAULT 0,
            stats_total_changes INTEGER DEFAULT 0,
            files_changed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        );

        CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repo_name);
        CREATE INDEX IF NOT EXISTS idx_commits_date ON commits(commit_date);

        CREATE TABLE IF NOT EXISTS commit_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commit_sha TEXT NOT NULL,
            repo_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            status TEXT,
            additions INTEGER DEFAULT 0,
            deletions INTEGER DEFAULT 0,
            changes INTEGER DEFAULT 0,
            patch TEXT,
            previous_filename TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        );

        CREATE INDEX IF NOT EXISTS idx_commit_files_sha ON commit_files(commit_sha);

        CREATE TABLE IF NOT EXISTS commit_summaries (
            commit_sha TEXT PRIMARY KEY,
            repo_name TEXT NOT NULL,
            summary_type TEXT,
            short_summary TEXT,
            detailed_summary TEXT,
            change_categories TEXT,
            impact_score REAL,
            risk_level TEXT,
            breaking_changes BOOLEAN DEFAULT FALSE,
            security_relevant BOOLEAN DEFAULT FALSE,
            performance_impact TEXT,
            complexity_score REAL,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        );

        -- Metrics tables
        CREATE TABLE IF NOT EXISTS repository_health_metrics (
            repo_name TEXT PRIMARY KEY,
            health_score REAL,
            activity_score REAL,
            collaboration_score REAL,
            security_score REAL,
            total_events INTEGER DEFAULT 0,
            unique_contributors INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        );

        CREATE TABLE IF NOT EXISTS developer_metrics (
            actor_login TEXT,
            repo_name TEXT,
            commits_count INTEGER DEFAULT 0,
            prs_opened INTEGER DEFAULT 0,
            prs_merged INTEGER DEFAULT 0,
            productivity_score REAL,
            time_period TEXT,
            period_start TEXT,
            period_end TEXT,
            last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            PRIMARY KEY (actor_login, repo_name, time_period, period_start)
        );

        CREATE TABLE IF NOT EXISTS security_metrics (
            repo_name TEXT,
            metric_type TEXT,
            severity TEXT,
            count INTEGER DEFAULT 0,
            date TEXT,
            last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            PRIMARY KEY (repo_name, metric_type, date)
        );
        """
    
    async def close(self) -> None:
        """Close SQLite connection."""
        # SQLite connections are opened per-operation, no persistent connection to close
        logger.info("SQLite connection closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check SQLite database health."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check if we can query the database
                cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = await cursor.fetchall()
                
                # Count total events
                cursor = await db.execute("SELECT COUNT(*) FROM events")
                event_count = (await cursor.fetchone())[0]
                
                return {
                    'status': 'healthy',
                    'provider': 'sqlite',
                    'db_path': self.db_path,
                    'tables_found': len(tables),
                    'total_events': event_count,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'sqlite',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


class SQLiteEventsRepository(EventsRepository):
    """SQLite implementation of EventsRepository."""
    
    def __init__(self, connection: SQLiteConnection):
        self.connection = connection
        self.db_path = connection.db_path
    
    async def insert_event(self, event_data: EventData) -> bool:
        """Insert a single event."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO events 
                    (id, event_type, repo_name, actor_login, created_at, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_data.get('id'),
                        event_data.get('event_type'),
                        event_data.get('repo_name'),
                        event_data.get('actor_login'),
                        self._format_datetime(event_data.get('created_at')),
                        json.dumps(event_data.get('payload', {}))
                    )
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to insert event: {e}")
            return False
    
    async def insert_events(self, events_data: List[EventData]) -> int:
        """Insert multiple events."""
        if not events_data:
            return 0
        
        inserted_count = 0
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for event_data in events_data:
                    try:
                        await db.execute(
                            """
                            INSERT OR IGNORE INTO events 
                            (id, event_type, repo_name, actor_login, created_at, payload)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                event_data.get('id'),
                                event_data.get('event_type'),
                                event_data.get('repo_name'),
                                event_data.get('actor_login'),
                                self._format_datetime(event_data.get('created_at')),
                                json.dumps(event_data.get('payload', {}))
                            )
                        )
                        inserted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to insert event {event_data.get('id')}: {e}")
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to insert events batch: {e}")
        
        return inserted_count
    
    async def get_events_by_type(
        self, 
        event_type: str,
        repo: Optional[str] = None,
        since_ts: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get events by type with optional filtering."""
        try:
            query = "SELECT * FROM events WHERE event_type = ?"
            params = [event_type]
            
            if repo:
                query += " AND repo_name = ?"
                params.append(repo)
            
            if since_ts:
                query += " AND created_at >= ?"
                params.append(self._format_datetime(since_ts))
            
            query += " ORDER BY created_at DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                return [self._convert_row_to_dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get events by type: {e}")
            return []
    
    async def count_events_by_type(
        self, 
        since_ts: Optional[datetime] = None,
        repo: Optional[str] = None
    ) -> Dict[str, int]:
        """Count events by type with optional filtering."""
        try:
            query = "SELECT event_type, COUNT(*) as count FROM events"
            params = []
            conditions = []
            
            if since_ts:
                conditions.append("created_at >= ?")
                params.append(self._format_datetime(since_ts))
            
            if repo:
                conditions.append("repo_name = ?")
                params.append(repo)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " GROUP BY event_type"
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                return {row[0]: row[1] for row in rows}
                
        except Exception as e:
            logger.error(f"Failed to count events by type: {e}")
            return {}
    
    async def get_trending_repositories(
        self, 
        since_ts: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending repositories based on event activity."""
        try:
            query = """
            SELECT 
                repo_name,
                COUNT(*) as total_events,
                COUNT(CASE WHEN event_type = 'WatchEvent' THEN 1 END) as watch_events,
                COUNT(CASE WHEN event_type = 'PullRequestEvent' THEN 1 END) as pr_events,
                COUNT(CASE WHEN event_type = 'IssuesEvent' THEN 1 END) as issue_events
            FROM events
            WHERE created_at >= ?
            GROUP BY repo_name
            ORDER BY total_events DESC
            LIMIT ?
            """
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, [self._format_datetime(since_ts), limit])
                rows = await cursor.fetchall()
                
                trending = []
                for row in rows:
                    trending.append({
                        'repo_name': row[0],
                        'total_events': row[1],
                        'event_breakdown': {
                            'WatchEvent': row[2],
                            'PullRequestEvent': row[3],
                            'IssuesEvent': row[4]
                        }
                    })
                
                return trending
                
        except Exception as e:
            logger.error(f"Failed to get trending repositories: {e}")
            return []
    
    async def get_repository_activity(
        self, 
        repo: str,
        since_ts: datetime
    ) -> Dict[str, Any]:
        """Get activity summary for a specific repository."""
        try:
            query = """
            SELECT event_type, COUNT(*) as count
            FROM events
            WHERE repo_name = ? AND created_at >= ?
            GROUP BY event_type
            """
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, [repo, self._format_datetime(since_ts)])
                rows = await cursor.fetchall()
                
                activity = {
                    'total_events': 0,
                    'event_breakdown': {}
                }
                
                for row in rows:
                    event_type, count = row
                    activity['event_breakdown'][event_type] = count
                    activity['total_events'] += count
                
                return activity
                
        except Exception as e:
            logger.error(f"Failed to get repository activity: {e}")
            return {'total_events': 0, 'event_breakdown': {}}
    
    def _format_datetime(self, dt: Any) -> str:
        """Format datetime for SQLite."""
        if isinstance(dt, datetime):
            return dt.isoformat()
        elif isinstance(dt, str):
            return dt
        else:
            return str(dt)
    
    def _convert_row_to_dict(self, row: aiosqlite.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary."""
        result = dict(row)
        
        # Parse JSON payload
        if 'payload' in result and isinstance(result['payload'], str):
            try:
                result['payload'] = json.loads(result['payload'])
            except json.JSONDecodeError:
                result['payload'] = {}
        
        return result


class SQLiteCommitsRepository(CommitsRepository):
    """SQLite implementation of CommitsRepository."""
    
    def __init__(self, connection: SQLiteConnection):
        self.connection = connection
        self.db_path = connection.db_path
    
    async def insert_commit(self, commit_data: CommitData) -> bool:
        """Insert a single commit."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO commits (
                        sha, repo_name, author_name, author_email, author_login,
                        committer_name, committer_email, message, commit_date,
                        push_event_id, branch_name, parent_shas, stats_additions,
                        stats_deletions, stats_total_changes, files_changed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        commit_data.get('sha'),
                        commit_data.get('repo_name'),
                        commit_data.get('author_name'),
                        commit_data.get('author_email'),
                        commit_data.get('author_login'),
                        commit_data.get('committer_name'),
                        commit_data.get('committer_email'),
                        commit_data.get('message'),
                        commit_data.get('commit_date'),
                        commit_data.get('push_event_id'),
                        commit_data.get('branch_name'),
                        commit_data.get('parent_shas'),
                        commit_data.get('stats_additions', 0),
                        commit_data.get('stats_deletions', 0),
                        commit_data.get('stats_total_changes', 0),
                        commit_data.get('files_changed', 0)
                    )
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to insert commit: {e}")
            return False
    
    async def insert_commit_files(
        self, 
        commit_sha: str,
        files_data: List[Dict[str, Any]]
    ) -> int:
        """Insert file changes for a commit."""
        if not files_data:
            return 0
        
        inserted_count = 0
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for file_data in files_data:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO commit_files (
                            commit_sha, repo_name, filename, status, additions,
                            deletions, changes, patch, previous_filename
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            commit_sha,
                            file_data.get('repo_name'),
                            file_data.get('filename'),
                            file_data.get('status'),
                            file_data.get('additions', 0),
                            file_data.get('deletions', 0),
                            file_data.get('changes', 0),
                            file_data.get('patch'),
                            file_data.get('previous_filename')
                        )
                    )
                    inserted_count += 1
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to insert commit files: {e}")
        
        return inserted_count
    
    async def insert_commit_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Insert commit summary and analysis."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO commit_summaries (
                        commit_sha, repo_name, summary_type, short_summary,
                        detailed_summary, change_categories, impact_score,
                        risk_level, breaking_changes, security_relevant,
                        performance_impact, complexity_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        summary_data.get('commit_sha'),
                        summary_data.get('repo_name'),
                        summary_data.get('summary_type'),
                        summary_data.get('short_summary'),
                        summary_data.get('detailed_summary'),
                        summary_data.get('change_categories'),
                        summary_data.get('impact_score'),
                        summary_data.get('risk_level'),
                        summary_data.get('breaking_changes', False),
                        summary_data.get('security_relevant', False),
                        summary_data.get('performance_impact'),
                        summary_data.get('complexity_score')
                    )
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to insert commit summary: {e}")
            return False
    
    async def get_commit(self, sha: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get commit by SHA and repository."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM commits WHERE sha = ? AND repo_name = ?",
                    [sha, repo]
                )
                row = await cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get commit: {e}")
            return None
    
    async def get_commit_files(self, sha: str, repo: str) -> List[Dict[str, Any]]:
        """Get file changes for a commit."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM commit_files WHERE commit_sha = ? AND repo_name = ?",
                    [sha, repo]
                )
                rows = await cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get commit files: {e}")
            return []
    
    async def get_recent_commits(
        self, 
        repo: str,
        since_ts: datetime,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent commits for a repository."""
        try:
            query = """
            SELECT 
                c.*,
                cs.short_summary, cs.detailed_summary, cs.change_categories,
                cs.impact_score, cs.risk_level, cs.breaking_changes,
                cs.security_relevant, cs.performance_impact
            FROM commits c
            LEFT JOIN commit_summaries cs ON c.sha = cs.commit_sha
            WHERE c.repo_name = ? AND c.commit_date >= ?
            ORDER BY c.commit_date DESC
            LIMIT ?
            """
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    query, 
                    [repo, since_ts.isoformat(), limit]
                )
                rows = await cursor.fetchall()
                
                commits = []
                for row in rows:
                    commit = dict(row)
                    # Separate summary data
                    if commit.get('short_summary'):
                        commit['summary'] = {
                            'short': commit.pop('short_summary', None),
                            'detailed': commit.pop('detailed_summary', None),
                            'categories': json.loads(commit.pop('change_categories', '[]') or '[]'),
                            'impact_score': commit.pop('impact_score', None),
                            'risk_level': commit.pop('risk_level', None),
                            'breaking_changes': bool(commit.pop('breaking_changes', False)),
                            'security_relevant': bool(commit.pop('security_relevant', False)),
                            'performance_impact': commit.pop('performance_impact', None)
                        }
                    
                    commits.append(commit)
                
                return commits
                
        except Exception as e:
            logger.error(f"Failed to get recent commits: {e}")
            return []
    
    async def get_commits_by_author(
        self, 
        repo: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get commit statistics grouped by author."""
        try:
            query = """
            SELECT 
                c.author_login,
                c.author_name,
                COUNT(*) as commit_count,
                SUM(c.stats_additions) as total_additions,
                SUM(c.stats_deletions) as total_deletions,
                SUM(c.files_changed) as total_files_changed,
                AVG(cs.impact_score) as avg_impact_score,
                COUNT(CASE WHEN cs.breaking_changes = 1 THEN 1 END) as breaking_commits,
                COUNT(CASE WHEN cs.security_relevant = 1 THEN 1 END) as security_commits
            FROM commits c
            LEFT JOIN commit_summaries cs ON c.sha = cs.commit_sha
            WHERE c.repo_name = ? AND c.commit_date >= ?
            GROUP BY c.author_login, c.author_name
            ORDER BY commit_count DESC
            """
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, [repo, since_ts.isoformat()])
                rows = await cursor.fetchall()
                
                authors = []
                for row in rows:
                    authors.append({
                        'author_login': row[0],
                        'author_name': row[1],
                        'commit_count': row[2],
                        'total_additions': row[3] or 0,
                        'total_deletions': row[4] or 0,
                        'total_files_changed': row[5] or 0,
                        'avg_impact_score': round(row[6], 2) if row[6] else 0,
                        'breaking_commits': row[7] or 0,
                        'security_commits': row[8] or 0
                    })
                
                return authors
                
        except Exception as e:
            logger.error(f"Failed to get commits by author: {e}")
            return []
    
    async def get_high_impact_commits(
        self, 
        repo: str,
        since_ts: datetime,
        min_impact_score: float = 70.0
    ) -> List[Dict[str, Any]]:
        """Get high-impact commits."""
        try:
            query = """
            SELECT 
                c.*,
                cs.short_summary, cs.detailed_summary, cs.change_categories,
                cs.impact_score, cs.risk_level, cs.breaking_changes,
                cs.security_relevant, cs.performance_impact
            FROM commits c
            JOIN commit_summaries cs ON c.sha = cs.commit_sha
            WHERE c.repo_name = ? AND c.commit_date >= ? AND cs.impact_score >= ?
            ORDER BY cs.impact_score DESC, c.commit_date DESC
            """
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    query, 
                    [repo, since_ts.isoformat(), min_impact_score]
                )
                rows = await cursor.fetchall()
                
                commits = []
                for row in rows:
                    commit = dict(row)
                    # Separate summary data
                    commit['summary'] = {
                        'short': commit.pop('short_summary', None),
                        'detailed': commit.pop('detailed_summary', None),
                        'categories': json.loads(commit.pop('change_categories', '[]') or '[]'),
                        'impact_score': commit.pop('impact_score', None),
                        'risk_level': commit.pop('risk_level', None),
                        'breaking_changes': bool(commit.pop('breaking_changes', False)),
                        'security_relevant': bool(commit.pop('security_relevant', False)),
                        'performance_impact': commit.pop('performance_impact', None)
                    }
                    commits.append(commit)
                
                return commits
                
        except Exception as e:
            logger.error(f"Failed to get high impact commits: {e}")
            return []


class SQLiteMetricsRepository(MetricsRepository):
    """SQLite implementation of MetricsRepository."""
    
    def __init__(self, connection: SQLiteConnection):
        self.connection = connection
        self.db_path = connection.db_path
    
    async def upsert_repository_health_metrics(self, metrics_data: MetricsData) -> bool:
        """Insert or update repository health metrics."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO repository_health_metrics (
                        repo_name, health_score, activity_score, collaboration_score,
                        security_score, total_events, unique_contributors
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metrics_data.get('repo_name'),
                        metrics_data.get('health_score'),
                        metrics_data.get('activity_score'),
                        metrics_data.get('collaboration_score'),
                        metrics_data.get('security_score'),
                        metrics_data.get('total_events', 0),
                        metrics_data.get('unique_contributors', 0)
                    )
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to upsert repository health metrics: {e}")
            return False
    
    async def get_repository_health_metrics(self, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository health metrics."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM repository_health_metrics WHERE repo_name = ?",
                    [repo]
                )
                row = await cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get repository health metrics: {e}")
            return None
    
    async def upsert_developer_metrics(self, metrics_data: MetricsData) -> bool:
        """Insert or update developer metrics."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO developer_metrics (
                        actor_login, repo_name, commits_count, prs_opened, prs_merged,
                        productivity_score, time_period, period_start, period_end
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metrics_data.get('actor_login'),
                        metrics_data.get('repo_name'),
                        metrics_data.get('commits_count', 0),
                        metrics_data.get('prs_opened', 0),
                        metrics_data.get('prs_merged', 0),
                        metrics_data.get('productivity_score'),
                        metrics_data.get('time_period'),
                        metrics_data.get('period_start'),
                        metrics_data.get('period_end')
                    )
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to upsert developer metrics: {e}")
            return False
    
    async def get_developer_metrics(
        self, 
        repo: str,
        time_period: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get developer metrics."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    """
                    SELECT * FROM developer_metrics 
                    WHERE repo_name = ? AND time_period = ? AND period_start >= ?
                    """,
                    [repo, time_period, since_ts.isoformat()]
                )
                rows = await cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get developer metrics: {e}")
            return []
    
    async def upsert_security_metrics(self, metrics_data: MetricsData) -> bool:
        """Insert or update security metrics."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO security_metrics (
                        repo_name, metric_type, severity, count, date
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        metrics_data.get('repo_name'),
                        metrics_data.get('metric_type'),
                        metrics_data.get('severity'),
                        metrics_data.get('count', 0),
                        metrics_data.get('date')
                    )
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to upsert security metrics: {e}")
            return False
    
    async def get_security_metrics(
        self, 
        repo: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get security metrics."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM security_metrics WHERE repo_name = ? AND date >= ?",
                    [repo, since_ts.date().isoformat()]
                )
                rows = await cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get security metrics: {e}")
            return []


class SQLiteManager(DatabaseManager):
    """SQLite implementation of DatabaseManager."""
    
    def __init__(self, connection: SQLiteConnection):
        super().__init__(connection)
        self._events = SQLiteEventsRepository(connection)
        self._commits = SQLiteCommitsRepository(connection)
        self._metrics = SQLiteMetricsRepository(connection)
    
    @property
    def events(self) -> EventsRepository:
        """Get events repository."""
        return self._events
    
    @property
    def commits(self) -> CommitsRepository:
        """Get commits repository."""
        return self._commits
    
    @property
    def metrics(self) -> MetricsRepository:
        """Get metrics repository."""
        return self._metrics