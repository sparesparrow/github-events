#!/usr/bin/env python3
"""
Manual Database Update Script

This script is designed to be used in GitHub Actions workflows to manually
update the database with events from specific repositories.

Usage:
    python scripts/manual_db_update.py --repos "owner/repo1,owner/repo2" --limit 300
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from github_events_monitor.collector import GitHubEventsCollector
from github_events_monitor.database import DatabaseManager


async def main():
    parser = argparse.ArgumentParser(description="Manually update GitHub events database")
    parser.add_argument(
        "--repos", 
        help="Comma-separated list of repositories (owner/repo,owner/repo2)",
        default=os.getenv("TARGET_REPOSITORIES", "")
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        help="Maximum number of events to collect per repository",
        default=300
    )
    parser.add_argument(
        "--db-path", 
        help="Database file path",
        default=os.getenv("DATABASE_PATH", "github_events.db")
    )
    parser.add_argument(
        "--github-token", 
        help="GitHub API token",
        default=os.getenv("GITHUB_TOKEN")
    )
    
    args = parser.parse_args()
    
    # Parse repositories
    repos = []
    if args.repos:
        repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    
    print(f"Target repositories: {repos}")
    print(f"Database path: {args.db_path}")
    print(f"Event limit: {args.limit}")
    
    # Initialize database manager and collector
    db_manager = DatabaseManager(args.db_path)
    await db_manager.initialize()
    
    collector = GitHubEventsCollector(
        db_path=args.db_path,
        github_token=args.github_token,
        target_repositories=repos if repos else None,
        db_manager=db_manager
    )
    
    # Collect and store events
    try:
        count = await collector.collect_and_store(limit=args.limit)
        print(f"Successfully collected {count} events")
        return count
    except Exception as e:
        print(f"Error collecting events: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
