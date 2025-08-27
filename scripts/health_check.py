#!/usr/bin/env python3
"""
Health Check Script

This script checks the health of the GitHub Events Monitor database and API.
Designed for use in GitHub Actions workflows and monitoring.

Usage:
    python scripts/health_check.py --db-path github_events.db
"""

import asyncio
import argparse
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from github_events_monitor.database import DatabaseManager


async def main():
    parser = argparse.ArgumentParser(description="Health check for GitHub Events Monitor")
    parser.add_argument(
        "--db-path", 
        help="Database file path",
        default=os.getenv("DATABASE_PATH", "github_events.db")
    )
    parser.add_argument(
        "--output", 
        help="Output format: json, text",
        choices=["json", "text"],
        default="text"
    )
    parser.add_argument(
        "--exit-on-error", 
        action="store_true",
        help="Exit with error code if health check fails"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize database manager and check aggregates
        db_manager = DatabaseManager(args.db_path)
        await db_manager.initialize()
        total = await db_manager.aggregates.get_total_events()
        status = {
            "status": "healthy",
            "database_connected": True,
            "total_events": total,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Format output
        if args.output == "json":
            print(json.dumps(status, indent=2))
        else:
            print(f"Status: {status['status']}")
            print(f"Database connected: {status['database_connected']}")
            print(f"Total events: {status['total_events']}")
            print(f"Timestamp: {status['timestamp']}")
            
            if status['status'] == 'unhealthy':
                print(f"Error: {status.get('error', 'Unknown error')}")
        
        # Exit with error if unhealthy and requested
        if args.exit_on_error and status['status'] == 'unhealthy':
            sys.exit(1)
            
    except Exception as e:
        error_msg = f"Health check failed: {e}"
        if args.output == "json":
            print(json.dumps({
                "status": "unhealthy",
                "database_connected": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, indent=2))
        else:
            print(error_msg)
        
        if args.exit_on_error:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
