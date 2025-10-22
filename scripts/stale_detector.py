#!/usr/bin/env python3
"""
Stale Detection Script

Detects stale pull requests and branches, and manages their lifecycle.
Supports cross-repository monitoring and automated cleanup.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from github import Github
from github.PullRequest import PullRequest
from github.Branch import Branch
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('stale_detector')

class StaleDetector:
    """Detect and manage stale pull requests and branches"""
    
    def __init__(self, github_token: str, repo_name: str = None):
        self.github = Github(github_token)
        self.repo_name = repo_name or self._get_current_repo()
        self.repo = self.github.get_repo(self.repo_name)
        
    def _get_current_repo(self) -> str:
        """Get current repository name from environment"""
        # Try to get from GitHub context
        github_repository = os.environ.get('GITHUB_REPOSITORY')
        if github_repository:
            return github_repository
        
        # Fallback to a default
        return 'sparesparrow/github-events'
    
    def detect_stale_pull_requests(self, days_stale: int = 30, 
                                 exclude_labels: List[str] = None) -> List[Dict[str, Any]]:
        """Detect stale pull requests"""
        if exclude_labels is None:
            exclude_labels = ['keep-open', 'stale-exempt', 'priority']
        
        logger.info(f"Detecting stale PRs older than {days_stale} days...")
        
        stale_prs = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_stale)
        
        # Get all open pull requests
        prs = self.repo.get_pulls(state='open', sort='updated', direction='desc')
        
        for pr in prs:
            try:
                # Check if PR has exempt labels
                pr_labels = [label.name for label in pr.labels]
                if any(label in pr_labels for label in exclude_labels):
                    logger.debug(f"PR #{pr.number} has exempt label, skipping")
                    continue
                
                # Check if PR is stale
                last_updated = pr.updated_at
                if last_updated < cutoff_date:
                    stale_pr = {
                        'number': pr.number,
                        'title': pr.title,
                        'url': pr.html_url,
                        'author': pr.user.login,
                        'created_at': pr.created_at.isoformat(),
                        'updated_at': last_updated.isoformat(),
                        'days_stale': (datetime.now(timezone.utc) - last_updated).days,
                        'labels': pr_labels,
                        'draft': pr.draft,
                        'mergeable': pr.mergeable,
                        'status': 'stale'
                    }
                    stale_prs.append(stale_pr)
                    logger.info(f"Found stale PR #{pr.number}: {pr.title}")
                
            except Exception as e:
                logger.error(f"Error processing PR #{pr.number}: {e}")
                continue
        
        logger.info(f"Found {len(stale_prs)} stale pull requests")
        return stale_prs
    
    def detect_stale_branches(self, days_stale: int = 30, 
                            protected_branches: List[str] = None) -> List[Dict[str, Any]]:
        """Detect stale branches"""
        if protected_branches is None:
            protected_branches = ['main', 'master', 'develop', 'dev']
        
        logger.info(f"Detecting stale branches older than {days_stale} days...")
        
        stale_branches = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_stale)
        
        # Get all branches
        branches = self.repo.get_branches()
        
        for branch in branches:
            try:
                # Skip protected branches
                if branch.name in protected_branches:
                    continue
                
                # Check if branch is stale
                last_commit = branch.commit.commit.committer.date
                if last_commit < cutoff_date:
                    # Check if branch has open PRs
                    open_prs = list(self.repo.get_pulls(head=f"{self.repo_name.split('/')[1]}:{branch.name}", state='open'))
                    
                    stale_branch = {
                        'name': branch.name,
                        'last_commit': last_commit.isoformat(),
                        'days_stale': (datetime.now(timezone.utc) - last_commit).days,
                        'open_prs': len(open_prs),
                        'protected': branch.protected,
                        'status': 'stale'
                    }
                    stale_branches.append(stale_branch)
                    logger.info(f"Found stale branch: {branch.name}")
                
            except Exception as e:
                logger.error(f"Error processing branch {branch.name}: {e}")
                continue
        
        logger.info(f"Found {len(stale_branches)} stale branches")
        return stale_branches
    
    def add_stale_labels(self, stale_prs: List[Dict[str, Any]], 
                        dry_run: bool = False) -> int:
        """Add stale labels to pull requests"""
        if dry_run:
            logger.info(f"DRY RUN: Would add stale labels to {len(stale_prs)} PRs")
            return len(stale_prs)
        
        labeled_count = 0
        for pr_data in stale_prs:
            try:
                pr = self.repo.get_pull(pr_data['number'])
                
                # Add stale label if not already present
                if 'stale' not in [label.name for label in pr.labels]:
                    pr.add_to_labels('stale')
                    labeled_count += 1
                    logger.info(f"Added stale label to PR #{pr_data['number']}")
                
            except Exception as e:
                logger.error(f"Failed to add stale label to PR #{pr_data['number']}: {e}")
        
        return labeled_count
    
    def close_stale_items(self, stale_prs: List[Dict[str, Any]], 
                         stale_branches: List[Dict[str, Any]], 
                         days_until_close: int = 7, 
                         dry_run: bool = False) -> Dict[str, int]:
        """Close stale pull requests and delete stale branches"""
        results = {'prs_closed': 0, 'branches_deleted': 0}
        
        if dry_run:
            logger.info(f"DRY RUN: Would close {len(stale_prs)} PRs and delete {len(stale_branches)} branches")
            return {'prs_closed': len(stale_prs), 'branches_deleted': len(stale_branches)}
        
        # Close stale PRs that are old enough
        close_cutoff = datetime.now(timezone.utc) - timedelta(days=days_until_close)
        
        for pr_data in stale_prs:
            try:
                last_updated = datetime.fromisoformat(pr_data['updated_at'].replace('Z', '+00:00'))
                if last_updated < close_cutoff:
                    pr = self.repo.get_pull(pr_data['number'])
                    pr.edit(state='closed')
                    results['prs_closed'] += 1
                    logger.info(f"Closed stale PR #{pr_data['number']}")
                
            except Exception as e:
                logger.error(f"Failed to close PR #{pr_data['number']}: {e}")
        
        # Delete stale branches (be very careful with this)
        for branch_data in stale_branches:
            try:
                # Only delete if no open PRs and not protected
                if (branch_data['open_prs'] == 0 and 
                    not branch_data['protected'] and
                    branch_data['days_stale'] > days_until_close):
                    
                    ref = self.repo.get_git_ref(f"heads/{branch_data['name']}")
                    ref.delete()
                    results['branches_deleted'] += 1
                    logger.info(f"Deleted stale branch: {branch_data['name']}")
                
            except Exception as e:
                logger.error(f"Failed to delete branch {branch_data['name']}: {e}")
        
        return results
    
    def generate_analysis_report(self, stale_prs: List[Dict[str, Any]], 
                               stale_branches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'repository': self.repo_name,
            'summary': {
                'total_stale_prs': len(stale_prs),
                'total_stale_branches': len(stale_branches),
                'oldest_pr_days': max([pr['days_stale'] for pr in stale_prs], default=0),
                'oldest_branch_days': max([branch['days_stale'] for branch in stale_branches], default=0)
            },
            'stale_prs': stale_prs,
            'stale_branches': stale_branches,
            'recommendations': self._generate_recommendations(stale_prs, stale_branches)
        }
        
        return report
    
    def _generate_recommendations(self, stale_prs: List[Dict[str, Any]], 
                                stale_branches: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on stale items"""
        recommendations = []
        
        if len(stale_prs) > 10:
            recommendations.append("High number of stale PRs - consider implementing PR review policies")
        
        if len(stale_branches) > 20:
            recommendations.append("High number of stale branches - consider implementing branch cleanup policies")
        
        # Check for very old items
        very_old_prs = [pr for pr in stale_prs if pr['days_stale'] > 90]
        if very_old_prs:
            recommendations.append(f"{len(very_old_prs)} PRs are over 90 days old - consider closing them")
        
        very_old_branches = [branch for branch in stale_branches if branch['days_stale'] > 90]
        if very_old_branches:
            recommendations.append(f"{len(very_old_branches)} branches are over 90 days old - consider deleting them")
        
        # Check for draft PRs
        draft_prs = [pr for pr in stale_prs if pr.get('draft', False)]
        if draft_prs:
            recommendations.append(f"{len(draft_prs)} draft PRs are stale - consider closing or completing them")
        
        return recommendations

def main():
    parser = argparse.ArgumentParser(description='Stale Detection Script')
    parser.add_argument('--token', required=True, help='GitHub token')
    parser.add_argument('--repo', help='Repository name (owner/repo)')
    parser.add_argument('--days-stale', type=int, default=30,
                       help='Days until PR/branch is considered stale')
    parser.add_argument('--days-close', type=int, default=7,
                       help='Days until stale PR/branch is closed')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (no actual changes)')
    parser.add_argument('--output', default='stale_analysis.json',
                       help='Output file for analysis results')
    parser.add_argument('--add-labels', action='store_true',
                       help='Add stale labels to PRs')
    parser.add_argument('--close-items', action='store_true',
                       help='Close stale PRs and delete stale branches')
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = StaleDetector(args.token, args.repo)
    
    # Detect stale items
    logger.info("Starting stale detection...")
    stale_prs = detector.detect_stale_pull_requests(args.days_stale)
    stale_branches = detector.detect_stale_branches(args.days_stale)
    
    # Add labels if requested
    if args.add_labels:
        labeled_count = detector.add_stale_labels(stale_prs, args.dry_run)
        logger.info(f"Labeled {labeled_count} PRs as stale")
    
    # Close items if requested
    if args.close_items:
        results = detector.close_stale_items(
            stale_prs, stale_branches, args.days_close, args.dry_run
        )
        logger.info(f"Closed {results['prs_closed']} PRs and deleted {results['branches_deleted']} branches")
    
    # Generate analysis report
    report = detector.generate_analysis_report(stale_prs, stale_branches)
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Analysis complete. Results saved to {args.output}")
    
    # Print summary
    print(f"\nStale Detection Summary:")
    print(f"Repository: {report['repository']}")
    print(f"Stale PRs: {report['summary']['total_stale_prs']}")
    print(f"Stale Branches: {report['summary']['total_stale_branches']}")
    print(f"Oldest PR: {report['summary']['oldest_pr_days']} days")
    print(f"Oldest Branch: {report['summary']['oldest_branch_days']} days")
    
    if report['recommendations']:
        print("\nRecommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")

if __name__ == '__main__':
    main()