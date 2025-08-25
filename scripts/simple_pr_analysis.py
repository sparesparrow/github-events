#!/usr/bin/env python3
"""
Simple script to calculate average time between PRs using existing MCP tools
"""

import requests
import json
from datetime import datetime
from typing import List, Dict

def fetch_prs_via_mcp(owner: str, repo: str) -> List[Dict]:
    """Fetch PRs using the MCP GitHub Events Monitor"""
    try:
        # Use the MCP server endpoint
        url = "http://localhost:8000/api/github/pull-requests"
        params = {
            "owner": owner,
            "repo": repo,
            "state": "all",
            "per_page": 100
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to MCP server: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return []

def calculate_avg_time_between_prs(prs: List[Dict]) -> Dict:
    """Calculate average time between consecutive PRs"""
    if len(prs) < 2:
        return {"error": "Need at least 2 PRs to calculate intervals"}
    
    # Sort PRs by creation date
    sorted_prs = sorted(prs, key=lambda x: x['created_at'])
    
    intervals = []
    for i in range(1, len(sorted_prs)):
        # Parse datetime strings
        prev_date = datetime.fromisoformat(sorted_prs[i-1]['created_at'].replace('Z', '+00:00'))
        curr_date = datetime.fromisoformat(sorted_prs[i]['created_at'].replace('Z', '+00:00'))
        
        # Calculate time difference in hours
        time_diff = (curr_date - prev_date).total_seconds() / 3600
        intervals.append(time_diff)
    
    avg_hours = sum(intervals) / len(intervals)
    avg_days = avg_hours / 24
    
    return {
        "total_prs": len(prs),
        "intervals": len(intervals),
        "avg_hours": round(avg_hours, 2),
        "avg_days": round(avg_days, 2),
        "min_interval_hours": round(min(intervals), 2),
        "max_interval_hours": round(max(intervals), 2)
    }

def main():
    owner = "sparesparrow"
    repo = "mcp-prompts"
    
    print(f"Fetching pull requests for {owner}/{repo}...")
    
    # Fetch PRs using MCP
    prs = fetch_prs_via_mcp(owner, repo)
    
    if not prs:
        print("No pull requests found or error occurred")
        return
    
    print(f"Found {len(prs)} pull requests")
    
    # Calculate timing
    result = calculate_avg_time_between_prs(prs)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    print("\n" + "="*50)
    print("PULL REQUEST TIMING ANALYSIS")
    print("="*50)
    print(f"Repository: {owner}/{repo}")
    print(f"Total PRs: {result['total_prs']}")
    print(f"Intervals calculated: {result['intervals']}")
    print(f"\nAverage time between PRs:")
    print(f"  {result['avg_hours']} hours")
    print(f"  {result['avg_days']} days")
    print(f"\nInterval range:")
    print(f"  Minimum: {result['min_interval_hours']} hours")
    print(f"  Maximum: {result['max_interval_hours']} hours")

if __name__ == "__main__":
    main()
