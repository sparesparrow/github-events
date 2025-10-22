#!/usr/bin/env python3
"""
Alert Manager Script

Manages alerts and notifications for stale items and other monitoring events.
Supports cross-domain cooperation and automated issue creation.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from github import Github
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('alert_manager')

class AlertManager:
    """Manage alerts and notifications"""
    
    def __init__(self, github_token: str, repo_name: str = None):
        self.github = Github(github_token)
        self.repo_name = repo_name or self._get_current_repo()
        self.repo = self.github.get_repo(self.repo_name)
        
    def _get_current_repo(self) -> str:
        """Get current repository name from environment"""
        github_repository = os.environ.get('GITHUB_REPOSITORY')
        if github_repository:
            return github_repository
        return 'sparesparrow/github-events'
    
    def create_stale_alert_issue(self, stale_data: Dict[str, Any], 
                                dry_run: bool = False) -> Optional[int]:
        """Create an issue for stale items alert"""
        if dry_run:
            logger.info("DRY RUN: Would create stale alert issue")
            return None
        
        # Determine alert level
        total_stale = (stale_data['summary']['total_stale_prs'] + 
                      stale_data['summary']['total_stale_branches'])
        
        if total_stale == 0:
            logger.info("No stale items to alert about")
            return None
        
        # Create issue title and body
        if total_stale > 20:
            emoji = "🚨"
            priority = "high"
        elif total_stale > 10:
            emoji = "⚠️"
            priority = "medium"
        else:
            emoji = "ℹ️"
            priority = "low"
        
        title = f"{emoji} Stale Items Alert - {total_stale} items need attention"
        
        body = self._generate_stale_alert_body(stale_data)
        
        # Create the issue
        try:
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=['stale-alert', f'priority-{priority}', 'automated']
            )
            logger.info(f"Created stale alert issue #{issue.number}")
            return issue.number
        except Exception as e:
            logger.error(f"Failed to create stale alert issue: {e}")
            return None
    
    def _generate_stale_alert_body(self, stale_data: Dict[str, Any]) -> str:
        """Generate issue body for stale alert"""
        summary = stale_data['summary']
        
        body = f"""## Stale Items Alert

**Repository:** {stale_data['repository']}
**Generated:** {stale_data['timestamp']}

### Summary
- **Stale PRs:** {summary['total_stale_prs']}
- **Stale Branches:** {summary['total_stale_branches']}
- **Oldest PR:** {summary['oldest_pr_days']} days old
- **Oldest Branch:** {summary['oldest_branch_days']} days old

### Stale Pull Requests
"""
        
        if stale_data['stale_prs']:
            for pr in stale_data['stale_prs'][:10]:  # Limit to first 10
                body += f"- [#{pr['number']} {pr['title']}]({pr['url']}) - {pr['days_stale']} days old\n"
            
            if len(stale_data['stale_prs']) > 10:
                body += f"- ... and {len(stale_data['stale_prs']) - 10} more\n"
        else:
            body += "No stale pull requests found.\n"
        
        body += "\n### Stale Branches\n"
        
        if stale_data['stale_branches']:
            for branch in stale_data['stale_branches'][:10]:  # Limit to first 10
                body += f"- `{branch['name']}` - {branch['days_stale']} days old"
                if branch['open_prs'] > 0:
                    body += f" ({branch['open_prs']} open PRs)"
                body += "\n"
            
            if len(stale_data['stale_branches']) > 10:
                body += f"- ... and {len(stale_data['stale_branches']) - 10} more\n"
        else:
            body += "No stale branches found.\n"
        
        # Add recommendations
        if stale_data['recommendations']:
            body += "\n### Recommendations\n"
            for i, rec in enumerate(stale_data['recommendations'], 1):
                body += f"{i}. {rec}\n"
        
        body += f"\n---\n*This alert was generated automatically by the stale detection system.*"
        
        return body
    
    def create_critical_alert(self, alert_data: Dict[str, Any], 
                            dry_run: bool = False) -> Optional[int]:
        """Create a critical alert issue"""
        if dry_run:
            logger.info("DRY RUN: Would create critical alert")
            return None
        
        title = f"🚨 CRITICAL ALERT - {alert_data.get('title', 'System Issue')}"
        
        body = f"""## Critical Alert

**Type:** {alert_data.get('type', 'Unknown')}
**Severity:** {alert_data.get('severity', 'Critical')}
**Generated:** {datetime.now(timezone.utc).isoformat()}

### Description
{alert_data.get('description', 'No description provided')}

### Details
```json
{json.dumps(alert_data.get('details', {}), indent=2)}
```

### Recommended Actions
{alert_data.get('recommended_actions', 'Please investigate immediately')}

---
*This is a critical alert that requires immediate attention.*
"""
        
        try:
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=['critical-alert', 'urgent', 'automated']
            )
            logger.info(f"Created critical alert issue #{issue.number}")
            return issue.number
        except Exception as e:
            logger.error(f"Failed to create critical alert: {e}")
            return None
    
    def create_ecosystem_alert(self, ecosystem_data: Dict[str, Any], 
                              dry_run: bool = False) -> Optional[int]:
        """Create an ecosystem monitoring alert"""
        if dry_run:
            logger.info("DRY RUN: Would create ecosystem alert")
            return None
        
        alert_level = ecosystem_data.get('alert_level', 'info')
        
        if alert_level == 'critical':
            emoji = "🚨"
            priority = "critical"
        elif alert_level == 'warning':
            emoji = "⚠️"
            priority = "high"
        else:
            emoji = "ℹ️"
            priority = "medium"
        
        title = f"{emoji} Ecosystem Alert - {alert_level.upper()}"
        
        body = f"""## Ecosystem Monitoring Alert

**Alert Level:** {alert_level.upper()}
**Generated:** {datetime.now(timezone.utc).isoformat()}

### Summary
{alert_data.get('summary', 'No summary available')}

### Details
```json
{json.dumps(ecosystem_data, indent=2)}
```

---
*This alert was generated by the ecosystem monitoring system.*
"""
        
        try:
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=['ecosystem-alert', f'priority-{priority}', 'automated']
            )
            logger.info(f"Created ecosystem alert issue #{issue.number}")
            return issue.number
        except Exception as e:
            logger.error(f"Failed to create ecosystem alert: {e}")
            return None
    
    def send_cross_domain_notification(self, target_repos: List[str], 
                                     notification_data: Dict[str, Any],
                                     dry_run: bool = False) -> List[Dict[str, Any]]:
        """Send notifications to other repositories"""
        results = []
        
        for repo in target_repos:
            if dry_run:
                logger.info(f"DRY RUN: Would send notification to {repo}")
                results.append({'repository': repo, 'success': True, 'dry_run': True})
                continue
            
            try:
                # Trigger repository_dispatch event
                url = f"https://api.github.com/repos/{repo}/dispatches"
                headers = {
                    'Authorization': f'token {self.github._Github__requester._Requester__authorizationHeader}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                payload = {
                    'event_type': 'ecosystem-alert',
                    'client_payload': notification_data
                }
                
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                results.append({'repository': repo, 'success': True})
                logger.info(f"Sent notification to {repo}")
                
            except Exception as e:
                logger.error(f"Failed to send notification to {repo}: {e}")
                results.append({'repository': repo, 'success': False, 'error': str(e)})
        
        return results
    
    def create_maintenance_issue(self, maintenance_data: Dict[str, Any],
                               dry_run: bool = False) -> Optional[int]:
        """Create a maintenance issue for scheduled tasks"""
        if dry_run:
            logger.info("DRY RUN: Would create maintenance issue")
            return None
        
        title = f"🔧 Maintenance Required - {maintenance_data.get('title', 'Scheduled Maintenance')}"
        
        body = f"""## Maintenance Required

**Type:** {maintenance_data.get('type', 'Scheduled')}
**Priority:** {maintenance_data.get('priority', 'Medium')}
**Generated:** {datetime.now(timezone.utc).isoformat()}

### Description
{maintenance_data.get('description', 'No description provided')}

### Tasks
{maintenance_data.get('tasks', 'No specific tasks listed')}

### Estimated Effort
{maintenance_data.get('estimated_effort', 'Unknown')}

---
*This is a maintenance issue generated by the monitoring system.*
"""
        
        try:
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=['maintenance', 'automated', maintenance_data.get('priority', 'medium')]
            )
            logger.info(f"Created maintenance issue #{issue.number}")
            return issue.number
        except Exception as e:
            logger.error(f"Failed to create maintenance issue: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Alert Manager Script')
    parser.add_argument('--token', required=True, help='GitHub token')
    parser.add_argument('--input', required=True, help='Input JSON file with alert data')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--alert-type', choices=['stale', 'critical', 'ecosystem', 'maintenance'],
                       default='stale', help='Type of alert to create')
    parser.add_argument('--target-repos', nargs='+',
                       default=['sparesparrow/github-events'],
                       help='Target repositories for cross-domain notifications')
    
    args = parser.parse_args()
    
    # Load input data
    try:
        with open(args.input, 'r') as f:
            input_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load input data: {e}")
        return 1
    
    # Initialize alert manager
    manager = AlertManager(args.token)
    
    # Create appropriate alert based on type
    issue_number = None
    
    if args.alert_type == 'stale':
        issue_number = manager.create_stale_alert_issue(input_data, args.dry_run)
    elif args.alert_type == 'critical':
        issue_number = manager.create_critical_alert(input_data, args.dry_run)
    elif args.alert_type == 'ecosystem':
        issue_number = manager.create_ecosystem_alert(input_data, args.dry_run)
    elif args.alert_type == 'maintenance':
        issue_number = manager.create_maintenance_issue(input_data, args.dry_run)
    
    # Send cross-domain notifications if specified
    if args.target_repos:
        notification_data = {
            'alert_type': args.alert_type,
            'data': input_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        results = manager.send_cross_domain_notification(
            args.target_repos, notification_data, args.dry_run
        )
        
        logger.info(f"Cross-domain notifications: {results}")
    
    # Print results
    if issue_number:
        print(f"Created {args.alert_type} alert issue #{issue_number}")
    else:
        print(f"No {args.alert_type} alert created")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())