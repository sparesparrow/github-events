#!/usr/bin/env python3
"""
Script to calculate average time between pull requests for a repository
using MCP GitHub Events Monitor
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any
import aiohttp
from dataclasses import dataclass

@dataclass
class PullRequest:
    number: int
    created_at: datetime
    closed_at: datetime = None
    merged_at: datetime = None

class PRTimingAnalyzer:
    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        self.mcp_server_url = mcp_server_url
        
    async def fetch_pull_requests(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetch pull requests using MCP server"""
        async with aiohttp.ClientSession() as session:
            # Use the MCP server's GitHub API endpoint
            url = f"{self.mcp_server_url}/api/github/pull-requests"
            params = {
                "owner": owner,
                "repo": repo,
                "state": "all",
                "per_page": 100  # Get maximum PRs
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error fetching PRs: {response.status}")
                    return []
    
    def parse_datetime(self, date_string: str) -> datetime:
        """Parse GitHub datetime string to datetime object"""
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    
    def calculate_time_intervals(self, prs: List[PullRequest]) -> List[float]:
        """Calculate time intervals between consecutive PRs in hours"""
        if len(prs) < 2:
            return []
        
        # Sort PRs by creation date
        sorted_prs = sorted(prs, key=lambda x: x.created_at)
        
        intervals = []
        for i in range(1, len(sorted_prs)):
            time_diff = sorted_prs[i].created_at - sorted_prs[i-1].created_at
            intervals.append(time_diff.total_seconds() / 3600)  # Convert to hours
        
        return intervals
    
    def analyze_pr_timing(self, owner: str, repo: str) -> Dict[str, Any]:
        """Main analysis function"""
        print(f"Analyzing pull request timing for {owner}/{repo}...")
        
        # Fetch PRs
        prs_data = asyncio.run(self.fetch_pull_requests(owner, repo))
        
        if not prs_data:
            return {"error": "No pull requests found or error fetching data"}
        
        # Convert to PullRequest objects
        prs = []
        for pr_data in prs_data:
            pr = PullRequest(
                number=pr_data['number'],
                created_at=self.parse_datetime(pr_data['created_at']),
                closed_at=self.parse_datetime(pr_data['closed_at']) if pr_data.get('closed_at') else None,
                merged_at=self.parse_datetime(pr_data['merged_at']) if pr_data.get('merged_at') else None
            )
            prs.append(pr)
        
        # Calculate intervals
        intervals = self.calculate_time_intervals(prs)
        
        if not intervals:
            return {"error": "Not enough PRs to calculate intervals"}
        
        # Calculate statistics
        avg_interval = sum(intervals) / len(intervals)
        min_interval = min(intervals)
        max_interval = max(intervals)
        
        # Convert to more readable formats
        avg_hours = avg_interval
        avg_days = avg_interval / 24
        
        return {
            "repository": f"{owner}/{repo}",
            "total_prs": len(prs),
            "intervals_calculated": len(intervals),
            "average_interval_hours": round(avg_hours, 2),
            "average_interval_days": round(avg_days, 2),
            "min_interval_hours": round(min_interval, 2),
            "max_interval_hours": round(max_interval, 2),
            "analysis_period": {
                "first_pr": prs[0].created_at.isoformat(),
                "last_pr": prs[-1].created_at.isoformat()
            }
        }

def main():
    if len(sys.argv) != 3:
        print("Usage: python pr_timing_analysis.py <owner> <repo>")
        print("Example: python pr_timing_analysis.py sparesparrow mcp-prompts")
        sys.exit(1)
    
    owner = sys.argv[1]
    repo = sys.argv[2]
    
    analyzer = PRTimingAnalyzer()
    result = analyzer.analyze_pr_timing(owner, repo)
    
    print("\n" + "="*50)
    print("PULL REQUEST TIMING ANALYSIS")
    print("="*50)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    print(f"Repository: {result['repository']}")
    print(f"Total PRs analyzed: {result['total_prs']}")
    print(f"Intervals calculated: {result['intervals_calculated']}")
    print(f"\nTiming Statistics:")
    print(f"  Average time between PRs: {result['average_interval_hours']} hours ({result['average_interval_days']} days)")
    print(f"  Minimum interval: {result['min_interval_hours']} hours")
    print(f"  Maximum interval: {result['max_interval_hours']} hours")
    print(f"\nAnalysis Period:")
    print(f"  First PR: {result['analysis_period']['first_pr']}")
    print(f"  Last PR: {result['analysis_period']['last_pr']}")

if __name__ == "__main__":
    main()
