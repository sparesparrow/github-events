#!/usr/bin/env python3
"""
Script to analyze MCP development trends using the GitHub Events Monitor MCP server
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from github_events_monitor.mcp_server import (
    collect_events_now,
    get_trending_repositories,
    get_repository_activity,
    get_avg_pr_interval,
    get_event_counts
)

async def analyze_mcp_development():
    """Analyze MCP development trends"""
    print("🔍 Analyzing MCP Development Trends...")
    print("=" * 50)
    
    # 1. Collect recent events
    print("\n1. Collecting recent GitHub events...")
    try:
        events_result = await collect_events_now(200)
        print(f"✅ Collected {events_result.get('events_collected', 0)} events")
    except Exception as e:
        print(f"❌ Error collecting events: {e}")
    
    # 2. Get trending repositories (focus on MCP-related)
    print("\n2. Finding trending repositories...")
    try:
        trending = await get_trending_repositories(hours=24, limit=20)
        print(f"✅ Found {trending.get('total_found', 0)} trending repositories")
        
        # Filter for MCP-related repositories
        mcp_repos = []
        for repo in trending.get('repositories', []):
            repo_name = repo.get('repo_name', '').lower()
            if any(keyword in repo_name for keyword in ['mcp', 'model-context', 'modelcontext']):
                mcp_repos.append(repo)
        
        print(f"📊 Found {len(mcp_repos)} MCP-related repositories:")
        for repo in mcp_repos[:10]:  # Show top 10
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
            activity = await get_repository_activity(repo_name, hours=24)
            if activity.get('success'):
                total_events = activity.get('total_events', 0)
                print(f"   Events (24h): {total_events}")
                
                # Show activity breakdown
                for event_type, data in activity.get('activity', {}).items():
                    count = data.get('count', 0)
                    if count > 0:
                        print(f"   - {event_type}: {count}")
            
            # Get PR frequency
            pr_data = await get_avg_pr_interval(repo_name)
            if pr_data.get('success') and pr_data.get('pr_count', 0) > 0:
                avg_interval = pr_data.get('avg_interval_hours', 0)
                print(f"   PR Frequency: {avg_interval:.1f} hours between PRs")
                print(f"   Activity Level: {pr_data.get('interpretation', {}).get('activity_level', 'Unknown')}")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {repo_name}: {e}")
    
    # 4. Get overall event counts
    print("\n4. Overall event statistics (last 24 hours)...")
    try:
        event_counts = await get_event_counts(1440)  # 24 hours in minutes
        if event_counts.get('success'):
            print(f"📊 Total events: {event_counts.get('total_events', 0)}")
            for event_type, count in event_counts.get('counts', {}).items():
                if count > 0:
                    print(f"   - {event_type}: {count}")
    except Exception as e:
        print(f"❌ Error getting event counts: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 MCP Development Analysis Complete!")
    print(f"📅 Analysis timestamp: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(analyze_mcp_development())
