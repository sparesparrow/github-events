import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional
import statistics
from dataclasses import dataclass

@dataclass
class PullRequest:
    number: int
    created_at: datetime
    closed_at: Optional[datetime]
    merged_at: Optional[datetime]
    state: str

class PRAnalyzer:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.headers = {}
        if github_token:
            self.headers['Authorization'] = f'token {github_token}'
        self.headers['Accept'] = 'application/vnd.github.v3+json'
    
    def get_pull_requests(self, owner: str, repo: str, state: str = "all") -> List[PullRequest]:
        """Fetch all pull requests for a repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {'state': state, 'per_page': 100, 'sort': 'created', 'direction': 'asc'}
        
        prs = []
        page = 1
        
        while True:
            params['page'] = page
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                break
                
            for pr_data in data:
                pr = PullRequest(
                    number=pr_data['number'],
                    created_at=datetime.fromisoformat(pr_data['created_at'].replace('Z', '+00:00')),
                    closed_at=datetime.fromisoformat(pr_data['closed_at'].replace('Z', '+00:00')) if pr_data['closed_at'] else None,
                    merged_at=datetime.fromisoformat(pr_data['merged_at'].replace('Z', '+00:00')) if pr_data['merged_at'] else None,
                    state=pr_data['state']
                )
                prs.append(pr)
            
            page += 1
            
            # GitHub API rate limiting
            if len(data) < 100:
                break
        
        return prs
    
    def calculate_average_time_between_prs(self, owner: str, repo: str) -> Dict:
        """Calculate average time between pull request creations"""
        prs = self.get_pull_requests(owner, repo)
        
        if len(prs) < 2:
            return {
                "error": "Not enough pull requests to calculate average time",
                "total_prs": len(prs),
                "average_time_days": None,
                "average_time_hours": None
            }
        
        # Sort by creation time
        prs.sort(key=lambda x: x.created_at)
        
        # Calculate time differences between consecutive PRs
        time_differences = []
        for i in range(1, len(prs)):
            time_diff = prs[i].created_at - prs[i-1].created_at
            time_differences.append(time_diff.total_seconds())
        
        # Calculate statistics
        avg_seconds = statistics.mean(time_differences)
        avg_hours = avg_seconds / 3600
        avg_days = avg_hours / 24
        
        # Calculate additional metrics
        median_seconds = statistics.median(time_differences)
        median_hours = median_seconds / 3600
        median_days = median_hours / 24
        
        return {
            "repository": f"{owner}/{repo}",
            "total_prs": len(prs),
            "time_period": {
                "first_pr": prs[0].created_at.isoformat(),
                "last_pr": prs[-1].created_at.isoformat(),
                "total_days": (prs[-1].created_at - prs[0].created_at).days
            },
            "average_time": {
                "days": round(avg_days, 2),
                "hours": round(avg_hours, 2),
                "seconds": round(avg_seconds, 2)
            },
            "median_time": {
                "days": round(median_days, 2),
                "hours": round(median_hours, 2),
                "seconds": round(median_seconds, 2)
            },
            "pr_frequency": {
                "prs_per_day": round(len(prs) / ((prs[-1].created_at - prs[0].created_at).days + 1), 2),
                "prs_per_week": round(len(prs) / (((prs[-1].created_at - prs[0].created_at).days + 1) / 7), 2)
            }
        }

def main():
    """Example usage for sparesparrow/mcp-prompts"""
    analyzer = PRAnalyzer()
    
    try:
        result = analyzer.calculate_average_time_between_prs("sparesparrow", "mcp-prompts")
        print("Pull Request Analysis Results:")
        print(f"Repository: {result['repository']}")
        print(f"Total PRs: {result['total_prs']}")
        print(f"Time Period: {result['time_period']['first_pr']} to {result['time_period']['last_pr']}")
        print(f"Total Days: {result['time_period']['total_days']}")
        print(f"\nAverage Time Between PRs:")
        print(f"  {result['average_time']['days']} days")
        print(f"  {result['average_time']['hours']} hours")
        print(f"\nMedian Time Between PRs:")
        print(f"  {result['median_time']['days']} days")
        print(f"  {result['median_time']['hours']} hours")
        print(f"\nPR Frequency:")
        print(f"  {result['pr_frequency']['prs_per_day']} PRs per day")
        print(f"  {result['pr_frequency']['prs_per_week']} PRs per week")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
