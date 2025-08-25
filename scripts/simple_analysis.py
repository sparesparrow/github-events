#!/usr/bin/env python3
"""
Simple script to analyze MCP development trends
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from github_events_monitor.collector import GitHubEventsCollector

async def main():
    """Main analysis function"""
    print("🔍 Analyzing MCP Development Trends...")
    print("=" * 50)
    
    # Initialize collector
    collector = GitHubEventsCollector("github_events.db", os.getenv("GITHUB_TOKEN"))
    await collector.initialize_database()
    
    # 1. Collect fresh events
    print("\n1. Collecting fresh GitHub events...")
    try:
        count = await collector.collect_and_store(100)
        print(f"✅ Collected {count} new events")
    except Exception as e:
        print(f"❌ Error collecting events: {e}")
    
    # 2. Get trending repositories
    print("\n2. Finding trending repositories...")
    try:
        trending = await collector.get_trending_repositories(24, 20)
        print(f"✅ Found {len(trending)} trending repositories")
        
        # Filter for MCP-related repositories
        mcp_repos = []
        for repo in trending:
            repo_name = repo.get('repo_name', '').lower()
            if any(keyword in repo_name for keyword in ['mcp', 'model-context', 'modelcontext']):
                mcp_repos.append(repo)
        
        print(f"📊 Found {len(mcp_repos)} MCP-related repositories:")
        for repo in mcp_repos[:10]:
            print(f"   - {repo.get('repo_name')}: {repo.get('event_count')} events")
            
    except Exception as e:
        print(f"❌ Error getting trending repos: {e}")
    
    # 3. Analyze specific MCP repositories
    print("\n3. Analyzing key MCP repositories...")
    key_repos = [
        'modelcontextprotocol/servers',
        'modelcontextprotocol/client-sdk',
        'modelcontextprotocol/specification',
        'anthropics/anthropic-cookbook',
        'microsoft/mcp',
        'openai/mcp'
    ]
    
    for repo_name in key_repos:
        try:
            print(f"\n📈 Analyzing {repo_name}...")
            
            # Get repository activity
            activity = await collector.get_repository_activity_summary(repo_name, 24)
            total_events = activity.get('total_events', 0)
            print(f"   Events (24h): {total_events}")
            
            # Show activity breakdown
            for event_type, data in activity.get('activity', {}).items():
                count = data.get('count', 0)
                if count > 0:
                    print(f"   - {event_type}: {count}")
            
            # Get PR frequency
            pr_data = await collector.get_avg_pr_interval(repo_name)
            if pr_data and pr_data.get('pr_count', 0) > 0:
                avg_interval = pr_data.get('avg_interval_hours', 0)
                print(f"   PR Frequency: {avg_interval:.1f} hours between PRs")
                print(f"   Total PRs tracked: {pr_data.get('pr_count', 0)}")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {repo_name}: {e}")
    
    # 4. Get overall event counts
    print("\n4. Overall event statistics (last 24 hours)...")
    try:
        event_counts = await collector.get_event_counts_by_type(1440)  # 24 hours in minutes
        total_events = sum(event_counts.values())
        print(f"📊 Total events: {total_events}")
        for event_type, count in event_counts.items():
            if count > 0:
                print(f"   - {event_type}: {count}")
    except Exception as e:
        print(f"❌ Error getting event counts: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 MCP Development Analysis Complete!")
    print(f"📅 Analysis timestamp: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
