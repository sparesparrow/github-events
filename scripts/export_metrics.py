#!/usr/bin/env python3
"""
Export Metrics Script

This script exports various metrics from the GitHub Events Monitor database.
Designed for use in GitHub Actions workflows for reporting and analysis.

Usage:
    python scripts/export_metrics.py --output metrics.json --hours 24
"""

import asyncio
import argparse
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from github_events_monitor.database import DatabaseManager
from github_events_monitor.services import MetricsService, EventsRepository


async def main():
    parser = argparse.ArgumentParser(description="Export metrics from GitHub Events Monitor")
    parser.add_argument(
        "--output", 
        help="Output file path (default: stdout)",
        default="-"
    )
    parser.add_argument(
        "--db-path", 
        help="Database file path",
        default=os.getenv("DATABASE_PATH", "github_events.db")
    )
    parser.add_argument(
        "--hours", 
        type=int,
        help="Hours to look back for metrics",
        default=24
    )
    parser.add_argument(
        "--trending-limit", 
        type=int,
        help="Number of trending repositories to include",
        default=10
    )
    parser.add_argument(
        "--repos", 
        help="Comma-separated list of specific repos to analyze",
        default=""
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(args.db_path)
        await db_manager.initialize()
        
        # Create services
        repository = EventsRepository(args.db_path)
        metrics_service = MetricsService(repository)
        
        # Collect metrics
        metrics = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "hours_lookback": args.hours,
            "event_counts": await metrics_service.get_event_counts(args.hours * 60),
            "trending_repositories": await metrics_service.get_trending(args.hours, args.trending_limit)
        }
        
        # Add specific repository metrics if requested
        if args.repos:
            repos = [r.strip() for r in args.repos.split(",") if r.strip()]
            metrics["repository_activity"] = {}
            
            for repo in repos:
                try:
                    activity = await metrics_service.get_repository_activity(repo, args.hours)
                    metrics["repository_activity"][repo] = activity
                except Exception as e:
                    metrics["repository_activity"][repo] = {"error": str(e)}
        
        # Output results
        if args.output == "-":
            print(json.dumps(metrics, indent=2))
        else:
            with open(args.output, 'w') as f:
                json.dump(metrics, f, indent=2)
            print(f"Metrics exported to {args.output}")
            
    except Exception as e:
        print(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
