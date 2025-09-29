#!/usr/bin/env python3
"""
Focused monitoring script for sparesparrow/ai-servis repository.

This script provides comprehensive monitoring and analytics specifically
tailored for the ai-servis repository.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from src.github_events_monitor.event_collector import GitHubEventsCollector
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Repository to monitor
TARGET_REPO = "sparesparrow/ai-servis"


async def setup_monitoring():
    """Set up monitoring for the ai-servis repository."""
    logger.info(f"🎯 Setting up focused monitoring for {TARGET_REPO}")
    
    # Create collector with GitHub token from environment
    github_token = os.getenv('GITHUB_TOKEN')
    collector = GitHubEventsCollector(
        db_path="ai_servis_events.db",
        github_token=github_token,
        target_repositories=[TARGET_REPO]
    )
    
    try:
        await collector.initialize_database()
        logger.info("✅ Monitoring system initialized")
        return collector
    except Exception as e:
        logger.error(f"❌ Failed to initialize monitoring: {e}")
        return None


async def collect_initial_data(collector):
    """Collect initial data for the repository."""
    logger.info(f"📡 Collecting initial data for {TARGET_REPO}...")
    
    try:
        # Fetch events from GitHub API
        events = await collector.fetch_repository_events(TARGET_REPO, limit=100)
        if events:
            # Store events
            stored_count = await collector.store_events(events)
            logger.info(f"✅ Collected {stored_count} events for {TARGET_REPO}")
            return stored_count > 0
        else:
            logger.info(f"ℹ️ No recent events found for {TARGET_REPO}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to collect initial data: {e}")
        return False


async def get_repository_overview(collector):
    """Get comprehensive overview of the repository."""
    logger.info(f"📊 Generating repository overview for {TARGET_REPO}...")
    
    overview = {
        'repository': TARGET_REPO,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'monitoring_active': True
    }
    
    try:
        # Health check
        health = await collector.health_check()
        overview['system_health'] = health
        
        # Event counts
        event_counts = await collector.get_event_counts_by_type(offset_minutes=168*60)  # Last week
        overview['event_counts'] = event_counts
        
        # Repository activity
        activity = await collector.get_repository_activity_summary(TARGET_REPO, hours=168)
        overview['activity_summary'] = activity
        
        # Try to get recent commits if available
        try:
            recent_commits = await collector.get_recent_commits(TARGET_REPO, hours=168, limit=20)
            overview['recent_commits'] = {
                'count': len(recent_commits),
                'commits': recent_commits[:5]  # Show top 5
            }
        except AttributeError:
            overview['recent_commits'] = {'count': 0, 'commits': [], 'note': 'Commit tracking not available'}
        
        # Try to get change summary if available  
        try:
            change_summary = await collector.get_repository_change_summary(TARGET_REPO, hours=168)
            overview['change_summary'] = change_summary
        except AttributeError:
            overview['change_summary'] = {'note': 'Change summary not available'}
        
        return overview
        
    except Exception as e:
        logger.error(f"❌ Failed to generate overview: {e}")
        overview['error'] = str(e)
        return overview


async def monitor_repository_health(collector):
    """Monitor repository health metrics."""
    logger.info(f"🏥 Analyzing repository health for {TARGET_REPO}...")
    
    try:
        # Get repository health score (if enhanced monitoring is available)
        if hasattr(collector, 'get_repository_health_score'):
            health_score = await collector.get_repository_health_score(TARGET_REPO, hours=168)
            
            print(f"\n🏥 Repository Health Report for {TARGET_REPO}")
            print("=" * 60)
            print(f"Overall Health Score: {health_score.get('health_score', 0):.1f}/100")
            print(f"Activity Score: {health_score.get('activity_score', 0):.1f}/100")
            print(f"Collaboration Score: {health_score.get('collaboration_score', 0):.1f}/100")
            print(f"Maintenance Score: {health_score.get('maintenance_score', 0):.1f}/100")
            print(f"Security Score: {health_score.get('security_score', 0):.1f}/100")
            print(f"Total Events: {health_score.get('total_events', 0)}")
            
            return health_score
        else:
            # Use basic activity summary
            activity = await collector.get_repository_activity_summary(TARGET_REPO, hours=168)
            
            print(f"\n📊 Repository Activity Report for {TARGET_REPO}")
            print("=" * 60)
            print(f"Total Events: {activity.get('total_events', 0)}")
            print(f"Activity Breakdown: {activity.get('activity', {})}")
            
            return activity
            
    except Exception as e:
        logger.error(f"❌ Failed to analyze repository health: {e}")
        return None


async def monitor_recent_activity(collector):
    """Monitor recent activity and changes."""
    logger.info(f"📈 Monitoring recent activity for {TARGET_REPO}...")
    
    try:
        # Get recent commits with summaries (if available)
        recent_commits = []
        if hasattr(collector, 'get_recent_commits'):
            recent_commits = await collector.get_recent_commits(TARGET_REPO, hours=24, limit=10)
        
        # Get basic repository activity
        activity = await collector.get_repository_activity_summary(TARGET_REPO, hours=24)
        
        print(f"\n📈 Recent Activity for {TARGET_REPO}")
        print("=" * 60)
        print(f"Total Events (last 24 hours): {activity.get('total_events', 0)}")
        
        # Show activity breakdown
        activity_breakdown = activity.get('activity', {})
        if activity_breakdown:
            print("\n📊 Event Breakdown:")
            for event_type, count in activity_breakdown.items():
                print(f"   {event_type}: {count}")
        
        # Show recent commits if available
        if recent_commits:
            print(f"\nRecent Commits: {len(recent_commits)}")
            for commit in recent_commits[:3]:  # Show top 3
                summary = commit.get('summary', {})
                print(f"\n📝 {commit.get('sha', 'unknown')[:8]} by {commit.get('author_login', 'unknown')}")
                print(f"   Message: {commit.get('message', 'No message')[:80]}...")
                if 'stats' in commit:
                    print(f"   Changes: +{commit.get('stats', {}).get('additions', 0)} -{commit.get('stats', {}).get('deletions', 0)}")
                    print(f"   Files: {commit.get('files_changed', 0)}")
                if summary:
                    print(f"   Impact: {summary.get('impact_score', 0):.1f}/100 ({summary.get('risk_level', 'unknown')} risk)")
        
        # Get change summary if available
        change_summary = {}
        if hasattr(collector, 'get_repository_change_summary'):
            try:
                change_summary = await collector.get_repository_change_summary(TARGET_REPO, hours=24)
            except Exception:
                change_summary = {'note': 'Change summary not available'}
        
        print(f"\n📊 Change Summary (last 24 hours):")
        stats = change_summary.get('statistics', {})
        print(f"   Total Commits: {stats.get('total_commits', 0)}")
        print(f"   Unique Authors: {stats.get('unique_authors', 0)}")
        print(f"   Lines Added: {stats.get('total_additions', 0)}")
        print(f"   Lines Deleted: {stats.get('total_deletions', 0)}")
        print(f"   Files Changed: {stats.get('total_files_changed', 0)}")
        
        categories = change_summary.get('change_categories', {})
        if categories:
            print(f"   Change Types: {', '.join(f'{k}({v})' for k, v in categories.items())}")
        
        return {
            'recent_commits': recent_commits,
            'change_summary': change_summary
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to monitor recent activity: {e}")
        return None


async def setup_continuous_monitoring(collector):
    """Set up continuous monitoring for the repository."""
    logger.info(f"🔄 Setting up continuous monitoring for {TARGET_REPO}...")
    
    try:
        # Start a background monitor for the repository
        monitor_id = collector.start_monitor(
            repository=TARGET_REPO,
            monitored_events=collector.MONITORED_EVENTS,
            interval_seconds=300  # 5 minutes
        )
        
        logger.info(f"✅ Started continuous monitor with ID: {monitor_id}")
        
        # Get active monitors
        active_monitors = collector.get_active_monitors()
        
        print(f"\n🔄 Continuous Monitoring Setup")
        print("=" * 60)
        print(f"Monitor ID: {monitor_id}")
        print(f"Repository: {TARGET_REPO}")
        print(f"Interval: 5 minutes")
        print(f"Events Monitored: {len(collector.MONITORED_EVENTS)}")
        print(f"Active Monitors: {len(active_monitors)}")
        
        return monitor_id
        
    except Exception as e:
        logger.error(f"❌ Failed to setup continuous monitoring: {e}")
        return None


async def generate_monitoring_report(collector):
    """Generate a comprehensive monitoring report."""
    logger.info(f"📋 Generating comprehensive monitoring report for {TARGET_REPO}...")
    
    report = {
        'repository': TARGET_REPO,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'report_type': 'comprehensive_monitoring'
    }
    
    try:
        # Basic repository info
        overview = await get_repository_overview(collector)
        report['overview'] = overview
        
        # Health metrics (if available)
        health = await monitor_repository_health(collector)
        if health:
            report['health_metrics'] = health
        
        # Recent activity
        activity = await monitor_recent_activity(collector)
        if activity:
            report['recent_activity'] = activity
        
        # Save report to file
        report_filename = f"ai_servis_monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Report saved to: {report_filename}")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Failed to generate monitoring report: {e}")
        report['error'] = str(e)
        return report


async def main():
    """Main monitoring function for ai-servis repository."""
    print(f"""
🎯 AI-Servis Repository Monitoring
==================================
Repository: {TARGET_REPO}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

This script will:
1. Initialize monitoring system
2. Collect initial data
3. Generate repository overview
4. Analyze repository health
5. Monitor recent activity
6. Set up continuous monitoring
7. Generate comprehensive report
""")
    
    # Initialize monitoring
    collector = await setup_monitoring()
    if not collector:
        print("❌ Failed to initialize monitoring system")
        return
    
    try:
        # Collect initial data
        print("\n📡 Step 1: Collecting Initial Data")
        has_data = await collect_initial_data(collector)
        
        if not has_data:
            print("⚠️ No recent data found. The repository might be inactive or private.")
        
        # Generate overview
        print("\n📊 Step 2: Repository Overview")
        overview = await get_repository_overview(collector)
        
        # Monitor health
        print("\n🏥 Step 3: Health Analysis")
        health = await monitor_repository_health(collector)
        
        # Monitor recent activity
        print("\n📈 Step 4: Recent Activity Analysis")
        activity = await monitor_recent_activity(collector)
        
        # Set up continuous monitoring
        print("\n🔄 Step 5: Continuous Monitoring Setup")
        monitor_id = await setup_continuous_monitoring(collector)
        
        # Generate comprehensive report
        print("\n📋 Step 6: Generating Comprehensive Report")
        report = await generate_monitoring_report(collector)
        
        print(f"\n✅ Monitoring setup complete for {TARGET_REPO}!")
        print("\n🌐 Available Endpoints:")
        print(f"   Health: http://localhost:8000/health")
        print(f"   Events: http://localhost:8000/metrics/event-counts?repo={TARGET_REPO}")
        print(f"   Activity: http://localhost:8000/metrics/repository-activity?repo={TARGET_REPO}")
        print(f"   Commits: http://localhost:8000/commits/recent?repo={TARGET_REPO}")
        print(f"   Health: http://localhost:8000/metrics/repository-health?repo={TARGET_REPO}")
        print(f"   Security: http://localhost:8000/metrics/security-monitoring?repo={TARGET_REPO}")
        
        if monitor_id:
            print(f"\n🔄 Continuous monitoring active (ID: {monitor_id})")
            print("   Data will be collected every 5 minutes")
            print("   Monitor status: http://localhost:8000/monitors")
        
        print(f"\n📄 Detailed report saved to: ai_servis_monitoring_report_*.json")
        
    except Exception as e:
        logger.error(f"❌ Monitoring failed: {e}")
        
    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())