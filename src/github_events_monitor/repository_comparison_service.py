"""
Repository Comparison Service

Provides specialized monitoring and comparison capabilities for repositories,
with focus on CI automation and development practices.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import aiohttp
import logging

from .config import config
from .event_collector import GitHubEventsCollector

logger = logging.getLogger(__name__)


@dataclass
class RepositoryMetrics:
    """Metrics for a single repository"""
    repo_name: str
    total_events: int
    workflow_runs: int
    deployments: int
    pull_requests: int
    issues: int
    commits: int
    releases: int
    security_events: int
    last_activity: Optional[datetime]
    avg_pr_merge_time: Optional[float]  # in hours
    workflow_success_rate: Optional[float]  # percentage


@dataclass
class ComparisonResult:
    """Result of comparing two repositories"""
    primary_repo: RepositoryMetrics
    comparison_repo: RepositoryMetrics
    comparison_summary: Dict[str, Any]
    ci_automation_analysis: Dict[str, Any]
    recommendations: List[str]


class RepositoryComparisonService:
    """Service for comparing repositories from CI automation perspective"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or config.github_token
        self.collector = GitHubEventsCollector(
            config.get_database_path(),
            self.github_token
        )
        
    async def get_repository_metrics(self, repo_name: str, hours: int = 168) -> RepositoryMetrics:
        """Get comprehensive metrics for a repository"""
        try:
            # Get basic event metrics
            activity_summary = await self.collector.get_repository_activity_summary(repo_name, hours)
            
            # Get workflow and CI specific data
            workflow_data = await self._get_workflow_metrics(repo_name, hours)
            pr_metrics = await self._get_pr_metrics(repo_name, hours)
            
            return RepositoryMetrics(
                repo_name=repo_name,
                total_events=activity_summary.get('total_events', 0),
                workflow_runs=workflow_data.get('workflow_runs', 0),
                deployments=workflow_data.get('deployments', 0),
                pull_requests=activity_summary.get('pull_request_events', 0),
                issues=activity_summary.get('issues_events', 0),
                commits=activity_summary.get('push_events', 0),
                releases=activity_summary.get('release_events', 0),
                security_events=workflow_data.get('security_events', 0),
                last_activity=activity_summary.get('last_activity'),
                avg_pr_merge_time=pr_metrics.get('avg_merge_time_hours'),
                workflow_success_rate=workflow_data.get('success_rate')
            )
        except Exception as e:
            logger.error(f"Error getting metrics for {repo_name}: {e}")
            return RepositoryMetrics(
                repo_name=repo_name,
                total_events=0,
                workflow_runs=0,
                deployments=0,
                pull_requests=0,
                issues=0,
                commits=0,
                releases=0,
                security_events=0,
                last_activity=None,
                avg_pr_merge_time=None,
                workflow_success_rate=None
            )
    
    async def _get_workflow_metrics(self, repo_name: str, hours: int) -> Dict[str, Any]:
        """Get workflow-specific metrics from GitHub API"""
        if not self.github_token:
            return {}
            
        try:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            since = datetime.now() - timedelta(hours=hours)
            since_str = since.isoformat() + 'Z'
            
            async with aiohttp.ClientSession() as session:
                # Get workflow runs
                workflow_url = f"https://api.github.com/repos/{repo_name}/actions/runs"
                params = {
                    'created': f'>={since_str}',
                    'per_page': 100
                }
                
                async with session.get(workflow_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        workflow_runs = data.get('workflow_runs', [])
                        
                        total_runs = len(workflow_runs)
                        successful_runs = len([run for run in workflow_runs if run.get('conclusion') == 'success'])
                        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else None
                        
                        # Count deployment-related workflows
                        deployment_runs = len([
                            run for run in workflow_runs 
                            if any(keyword in run.get('name', '').lower() 
                                  for keyword in ['deploy', 'release', 'publish', 'pages'])
                        ])
                        
                        # Count security-related workflows
                        security_runs = len([
                            run for run in workflow_runs
                            if any(keyword in run.get('name', '').lower()
                                  for keyword in ['security', 'codeql', 'scan', 'audit'])
                        ])
                        
                        return {
                            'workflow_runs': total_runs,
                            'deployments': deployment_runs,
                            'security_events': security_runs,
                            'success_rate': success_rate
                        }
                    else:
                        logger.warning(f"Failed to get workflow data for {repo_name}: {response.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Error getting workflow metrics for {repo_name}: {e}")
            return {}
    
    async def _get_pr_metrics(self, repo_name: str, hours: int) -> Dict[str, Any]:
        """Get pull request metrics"""
        try:
            # Use existing collector method
            pr_data = await self.collector.get_avg_pr_interval(repo_name)
            
            # Convert to hours if we have the data
            avg_hours = None
            if pr_data.get('avg_interval_seconds'):
                avg_hours = pr_data['avg_interval_seconds'] / 3600
                
            return {
                'avg_merge_time_hours': avg_hours,
                'total_prs': pr_data.get('total_events', 0)
            }
        except Exception as e:
            logger.error(f"Error getting PR metrics for {repo_name}: {e}")
            return {}
    
    async def compare_repositories(
        self, 
        primary_repo: str, 
        comparison_repo: str,
        hours: int = 168
    ) -> ComparisonResult:
        """Compare two repositories from CI automation perspective"""
        
        # Get metrics for both repositories
        primary_metrics = await self.get_repository_metrics(primary_repo, hours)
        comparison_metrics = await self.get_repository_metrics(comparison_repo, hours)
        
        # Generate comparison analysis
        comparison_summary = self._generate_comparison_summary(primary_metrics, comparison_metrics)
        ci_analysis = self._analyze_ci_automation(primary_metrics, comparison_metrics)
        recommendations = self._generate_recommendations(primary_metrics, comparison_metrics)
        
        return ComparisonResult(
            primary_repo=primary_metrics,
            comparison_repo=comparison_metrics,
            comparison_summary=comparison_summary,
            ci_automation_analysis=ci_analysis,
            recommendations=recommendations
        )
    
    def _generate_comparison_summary(
        self, 
        primary: RepositoryMetrics, 
        comparison: RepositoryMetrics
    ) -> Dict[str, Any]:
        """Generate summary comparison between repositories"""
        
        def safe_ratio(a, b):
            return (a / b) if b > 0 else None
            
        def safe_percentage_diff(a, b):
            if b == 0:
                return None
            return ((a - b) / b) * 100
        
        return {
            'activity_comparison': {
                'primary_total_events': primary.total_events,
                'comparison_total_events': comparison.total_events,
                'activity_ratio': safe_ratio(primary.total_events, comparison.total_events),
                'activity_difference_percent': safe_percentage_diff(primary.total_events, comparison.total_events)
            },
            'ci_automation_comparison': {
                'primary_workflow_runs': primary.workflow_runs,
                'comparison_workflow_runs': comparison.workflow_runs,
                'workflow_ratio': safe_ratio(primary.workflow_runs, comparison.workflow_runs),
                'primary_success_rate': primary.workflow_success_rate,
                'comparison_success_rate': comparison.workflow_success_rate
            },
            'development_velocity': {
                'primary_commits': primary.commits,
                'comparison_commits': comparison.commits,
                'primary_prs': primary.pull_requests,
                'comparison_prs': comparison.pull_requests,
                'primary_avg_pr_time': primary.avg_pr_merge_time,
                'comparison_avg_pr_time': comparison.avg_pr_merge_time
            },
            'deployment_comparison': {
                'primary_deployments': primary.deployments,
                'comparison_deployments': comparison.deployments,
                'primary_releases': primary.releases,
                'comparison_releases': comparison.releases
            }
        }
    
    def _analyze_ci_automation(
        self, 
        primary: RepositoryMetrics, 
        comparison: RepositoryMetrics
    ) -> Dict[str, Any]:
        """Analyze CI automation practices"""
        
        analysis = {
            'automation_maturity': {},
            'workflow_patterns': {},
            'deployment_practices': {},
            'quality_assurance': {}
        }
        
        # Automation maturity analysis
        primary_automation_score = self._calculate_automation_score(primary)
        comparison_automation_score = self._calculate_automation_score(comparison)
        
        analysis['automation_maturity'] = {
            'primary_score': primary_automation_score,
            'comparison_score': comparison_automation_score,
            'maturity_leader': 'primary' if primary_automation_score > comparison_automation_score else 'comparison',
            'score_difference': abs(primary_automation_score - comparison_automation_score)
        }
        
        # Workflow patterns
        analysis['workflow_patterns'] = {
            'primary_workflow_frequency': primary.workflow_runs / max(primary.total_events, 1),
            'comparison_workflow_frequency': comparison.workflow_runs / max(comparison.total_events, 1),
            'primary_deployment_frequency': primary.deployments / max(primary.workflow_runs, 1),
            'comparison_deployment_frequency': comparison.deployments / max(comparison.workflow_runs, 1)
        }
        
        # Quality assurance
        analysis['quality_assurance'] = {
            'primary_success_rate': primary.workflow_success_rate,
            'comparison_success_rate': comparison.workflow_success_rate,
            'primary_security_focus': primary.security_events / max(primary.workflow_runs, 1),
            'comparison_security_focus': comparison.security_events / max(comparison.workflow_runs, 1)
        }
        
        return analysis
    
    def _calculate_automation_score(self, metrics: RepositoryMetrics) -> float:
        """Calculate automation maturity score (0-100)"""
        score = 0
        
        # Workflow automation (30 points)
        if metrics.workflow_runs > 0:
            score += 30
            
        # Deployment automation (25 points)
        if metrics.deployments > 0:
            score += 25
            
        # Success rate (20 points)
        if metrics.workflow_success_rate:
            score += (metrics.workflow_success_rate / 100) * 20
            
        # Security automation (15 points)
        if metrics.security_events > 0:
            score += 15
            
        # Release automation (10 points)
        if metrics.releases > 0:
            score += 10
            
        return min(score, 100)
    
    def _generate_recommendations(
        self, 
        primary: RepositoryMetrics, 
        comparison: RepositoryMetrics
    ) -> List[str]:
        """Generate recommendations based on comparison"""
        recommendations = []
        
        # Compare workflow automation
        if primary.workflow_runs < comparison.workflow_runs:
            recommendations.append(
                f"Consider increasing CI automation - {comparison.repo_name} has {comparison.workflow_runs} workflow runs vs {primary.workflow_runs}"
            )
        
        # Compare success rates
        if (primary.workflow_success_rate and comparison.workflow_success_rate and 
            primary.workflow_success_rate < comparison.workflow_success_rate):
            recommendations.append(
                f"Improve workflow reliability - {comparison.repo_name} has {comparison.workflow_success_rate:.1f}% success rate vs {primary.workflow_success_rate:.1f}%"
            )
        
        # Compare deployment frequency
        if primary.deployments < comparison.deployments:
            recommendations.append(
                f"Consider more frequent deployments - {comparison.repo_name} has {comparison.deployments} deployments vs {primary.deployments}"
            )
        
        # Compare security automation
        if primary.security_events < comparison.security_events:
            recommendations.append(
                f"Enhance security automation - {comparison.repo_name} has {comparison.security_events} security-related workflows vs {primary.security_events}"
            )
        
        # Compare PR merge times
        if (primary.avg_pr_merge_time and comparison.avg_pr_merge_time and
            primary.avg_pr_merge_time > comparison.avg_pr_merge_time):
            recommendations.append(
                f"Optimize PR review process - {comparison.repo_name} has {comparison.avg_pr_merge_time:.1f}h avg merge time vs {primary.avg_pr_merge_time:.1f}h"
            )
        
        if not recommendations:
            recommendations.append("Both repositories show similar CI automation patterns")
            
        return recommendations

    async def get_comparison_dashboard_data(self) -> Dict[str, Any]:
        """Get data for repository comparison dashboard"""
        primary_repos = config.primary_repositories or ["openssl/openssl"]
        comparison_repos = config.comparison_repositories or ["sparesparrow/github-events"]
        
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'comparisons': [],
            'summary': {}
        }
        
        # Perform comparisons
        for primary_repo in primary_repos:
            for comparison_repo in comparison_repos:
                try:
                    comparison_result = await self.compare_repositories(primary_repo, comparison_repo)
                    dashboard_data['comparisons'].append({
                        'primary_repo': primary_repo,
                        'comparison_repo': comparison_repo,
                        'metrics': {
                            'primary': comparison_result.primary_repo.__dict__,
                            'comparison': comparison_result.comparison_repo.__dict__
                        },
                        'analysis': comparison_result.ci_automation_analysis,
                        'recommendations': comparison_result.recommendations
                    })
                except Exception as e:
                    logger.error(f"Error comparing {primary_repo} vs {comparison_repo}: {e}")
        
        return dashboard_data