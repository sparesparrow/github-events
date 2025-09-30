#!/usr/bin/env python3
"""
Comprehensive MCP Development Analysis
"""

import asyncio
import sys
import os
import httpx
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from github_events_monitor.collector import GitHubEventsCollector

async def collect_mcp_events():
    """Collect events specifically from MCP repositories"""
    print("🔍 Collecting MCP-specific events...")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ No GitHub token found")
        return
    
    # MCP-related repositories to monitor
    mcp_repos = [
        "modelcontextprotocol/servers",
        "modelcontextprotocol/client-sdk", 
        "modelcontextprotocol/specification",
        "modelcontextprotocol/mcp",
        "anthropics/anthropic-cookbook",
        "microsoft/mcp",
        "openai/mcp",
        "anthropics/anthropic-sdk-python",
        "anthropics/anthropic-sdk-typescript",
        "microsoft/vscode-mcp",
        "microsoft/mcp-server-samples",
        "openai/mcp-server-samples"
    ]
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"token {github_token}"}
        
        for repo in mcp_repos:
            try:
                print(f"📡 Checking {repo}...")
                
                # Get repository events
                url = f"https://api.github.com/repos/{repo}/events"
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    events = response.json()
                    print(f"   ✅ Found {len(events)} events")
                    
                    # Process events (simplified - just count them)
                    event_types = {}
                    for event in events[:10]:  # Limit to recent 10
                        event_type = event.get('type', 'Unknown')
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                    
                    for event_type, count in event_types.items():
                        print(f"   - {event_type}: {count}")
                        
                elif response.status_code == 404:
                    print(f"   ❌ Repository not found: {repo}")
                else:
                    print(f"   ⚠️  Status {response.status_code}: {repo}")
                    
            except Exception as e:
                print(f"   ❌ Error checking {repo}: {e}")
            
            # Rate limiting
            await asyncio.sleep(1)

async def analyze_github_trends():
    """Analyze general GitHub trends for MCP-related activity"""
    print("\n📊 Analyzing GitHub trends for MCP development...")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ No GitHub token found")
        return
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"token {github_token}"}
        
        # Search for MCP-related repositories
        search_terms = [
            "mcp model context protocol",
            "modelcontextprotocol",
            "mcp-server",
            "mcp-client"
        ]
        
        for term in search_terms:
            try:
                print(f"\n🔍 Searching for: '{term}'")
                url = f"https://api.github.com/search/repositories?q={term}&sort=updated&order=desc&per_page=10"
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    results = response.json()
                    print(f"   Found {results['total_count']} repositories")
                    
                    for repo in results['items'][:5]:
                        name = repo['full_name']
                        stars = repo['stargazers_count']
                        updated = repo['updated_at']
                        description = repo['description'] or "No description"
                        print(f"   - {name} (⭐{stars}) - {description[:60]}...")
                        
                else:
                    print(f"   ❌ Search failed: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error searching '{term}': {e}")
            
            await asyncio.sleep(1)

async def check_mcp_ecosystem():
    """Check the broader MCP ecosystem"""
    print("\n🌐 Checking MCP Ecosystem...")
    
    # Key organizations and their MCP-related repositories
    orgs = {
        "modelcontextprotocol": [
            "servers", "client-sdk", "specification", "mcp"
        ],
        "anthropics": [
            "anthropic-cookbook", "anthropic-sdk-python", "anthropic-sdk-typescript"
        ],
        "microsoft": [
            "mcp", "vscode-mcp", "mcp-server-samples"
        ],
        "openai": [
            "mcp", "mcp-server-samples"
        ]
    }
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ No GitHub token found")
        return
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"token {github_token}"}
        
        for org, repos in orgs.items():
            print(f"\n🏢 {org.upper()}:")
            
            for repo in repos:
                try:
                    repo_name = f"{org}/{repo}"
                    url = f"https://api.github.com/repos/{repo_name}"
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        repo_data = response.json()
                        stars = repo_data['stargazers_count']
                        forks = repo_data['forks_count']
                        updated = repo_data['updated_at']
                        description = repo_data['description'] or "No description"
                        
                        print(f"   ✅ {repo_name}")
                        print(f"      ⭐ {stars} | 🍴 {forks} | 📅 {updated[:10]}")
                        print(f"      📝 {description[:80]}...")
                        
                    elif response.status_code == 404:
                        print(f"   ❌ {repo_name} - Not found")
                    else:
                        print(f"   ⚠️  {repo_name} - Status {response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Error checking {repo_name}: {e}")
                
                await asyncio.sleep(0.5)

async def main():
    """Main analysis function"""
    print("🚀 Comprehensive MCP Development Analysis")
    print("=" * 60)
    print(f"📅 Analysis started: {datetime.now().isoformat()}")
    
    # Initialize our collector
    collector = GitHubEventsCollector("github_events.db", os.getenv("GITHUB_TOKEN"))
    await collector.initialize_database()
    
    # Collect more events
    print("\n1. Collecting GitHub events...")
    try:
        count = await collector.collect_and_store(200)
        print(f"✅ Collected {count} new events")
    except Exception as e:
        print(f"❌ Error collecting events: {e}")
    
    # Analyze MCP ecosystem
    await check_mcp_ecosystem()
    
    # Analyze GitHub trends
    await analyze_github_trends()
    
    # Collect MCP-specific events
    await collect_mcp_events()
    
    print("\n" + "=" * 60)
    print("🎯 Analysis Complete!")
    print(f"📅 Analysis finished: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
