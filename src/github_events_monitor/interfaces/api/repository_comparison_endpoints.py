"""
Repository Comparison API Endpoints

Provides REST API endpoints for repository comparison and CI automation monitoring.
"""

from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Query
from datetime import datetime
import logging

from ...repository_comparison_service import RepositoryComparisonService
from ...config import config

logger = logging.getLogger(__name__)


class RepositoryComparisonEndpoint:
    """Endpoint for comparing repositories"""
    
    def __init__(self):
        self.comparison_service = RepositoryComparisonService()
    
    async def compare_repositories(
        self,
        primary_repo: str = Query(..., description="Primary repository to compare (e.g., 'openssl/openssl')"),
        comparison_repo: str = Query(..., description="Repository to compare against (e.g., 'sparesparrow/github-events')"),
        hours: int = Query(168, description="Time window in hours for comparison (default: 168 = 1 week)")
    ) -> Dict[str, Any]:
        """Compare two repositories from CI automation perspective"""
        try:
            if hours <= 0 or hours > 8760:  # Max 1 year
                raise HTTPException(status_code=400, detail="Hours must be between 1 and 8760")
            
            comparison_result = await self.comparison_service.compare_repositories(
                primary_repo, comparison_repo, hours
            )
            
            return {
                "comparison": {
                    "primary_repository": primary_repo,
                    "comparison_repository": comparison_repo,
                    "time_window_hours": hours,
                    "generated_at": datetime.now().isoformat()
                },
                "metrics": {
                    "primary": {
                        "repo_name": comparison_result.primary_repo.repo_name,
                        "total_events": comparison_result.primary_repo.total_events,
                        "workflow_runs": comparison_result.primary_repo.workflow_runs,
                        "deployments": comparison_result.primary_repo.deployments,
                        "pull_requests": comparison_result.primary_repo.pull_requests,
                        "issues": comparison_result.primary_repo.issues,
                        "commits": comparison_result.primary_repo.commits,
                        "releases": comparison_result.primary_repo.releases,
                        "security_events": comparison_result.primary_repo.security_events,
                        "avg_pr_merge_time_hours": comparison_result.primary_repo.avg_pr_merge_time,
                        "workflow_success_rate": comparison_result.primary_repo.workflow_success_rate
                    },
                    "comparison": {
                        "repo_name": comparison_result.comparison_repo.repo_name,
                        "total_events": comparison_result.comparison_repo.total_events,
                        "workflow_runs": comparison_result.comparison_repo.workflow_runs,
                        "deployments": comparison_result.comparison_repo.deployments,
                        "pull_requests": comparison_result.comparison_repo.pull_requests,
                        "issues": comparison_result.comparison_repo.issues,
                        "commits": comparison_result.comparison_repo.commits,
                        "releases": comparison_result.comparison_repo.releases,
                        "security_events": comparison_result.comparison_repo.security_events,
                        "avg_pr_merge_time_hours": comparison_result.comparison_repo.avg_pr_merge_time,
                        "workflow_success_rate": comparison_result.comparison_repo.workflow_success_rate
                    }
                },
                "analysis": comparison_result.ci_automation_analysis,
                "summary": comparison_result.comparison_summary,
                "recommendations": comparison_result.recommendations
            }
            
        except Exception as e:
            logger.error(f"Error comparing repositories {primary_repo} vs {comparison_repo}: {e}")
            raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


class RepositoryMetricsEndpoint:
    """Endpoint for getting detailed repository metrics"""
    
    def __init__(self):
        self.comparison_service = RepositoryComparisonService()
    
    async def get_repository_metrics(
        self,
        repo: str = Query(..., description="Repository name (e.g., 'openssl/openssl')"),
        hours: int = Query(168, description="Time window in hours (default: 168 = 1 week)")
    ) -> Dict[str, Any]:
        """Get comprehensive metrics for a single repository"""
        try:
            if hours <= 0 or hours > 8760:  # Max 1 year
                raise HTTPException(status_code=400, detail="Hours must be between 1 and 8760")
            
            metrics = await self.comparison_service.get_repository_metrics(repo, hours)
            
            return {
                "repository": repo,
                "time_window_hours": hours,
                "generated_at": datetime.now().isoformat(),
                "metrics": {
                    "total_events": metrics.total_events,
                    "workflow_runs": metrics.workflow_runs,
                    "deployments": metrics.deployments,
                    "pull_requests": metrics.pull_requests,
                    "issues": metrics.issues,
                    "commits": metrics.commits,
                    "releases": metrics.releases,
                    "security_events": metrics.security_events,
                    "last_activity": metrics.last_activity.isoformat() if metrics.last_activity else None,
                    "avg_pr_merge_time_hours": metrics.avg_pr_merge_time,
                    "workflow_success_rate": metrics.workflow_success_rate
                },
                "automation_score": self.comparison_service._calculate_automation_score(metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics for repository {repo}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


class ComparisonDashboardEndpoint:
    """Endpoint for getting comparison dashboard data"""
    
    def __init__(self):
        self.comparison_service = RepositoryComparisonService()
    
    async def get_dashboard_data(
        self,
        hours: int = Query(168, description="Time window in hours (default: 168 = 1 week)")
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard data for configured repository comparisons"""
        try:
            if hours <= 0 or hours > 8760:  # Max 1 year
                raise HTTPException(status_code=400, detail="Hours must be between 1 and 8760")
            
            dashboard_data = await self.comparison_service.get_comparison_dashboard_data()
            
            # Add configuration info
            dashboard_data.update({
                "configuration": {
                    "primary_repositories": config.primary_repositories,
                    "comparison_repositories": config.comparison_repositories,
                    "monitoring_focus_areas": config.monitoring_focus_areas,
                    "time_window_hours": hours
                }
            })
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error generating dashboard data: {e}")
            raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


class CIAutomationAnalysisEndpoint:
    """Endpoint for CI automation analysis"""
    
    def __init__(self):
        self.comparison_service = RepositoryComparisonService()
    
    async def analyze_ci_automation(
        self,
        repo: str = Query(..., description="Repository name (e.g., 'openssl/openssl')"),
        hours: int = Query(168, description="Time window in hours (default: 168 = 1 week)")
    ) -> Dict[str, Any]:
        """Analyze CI automation practices for a repository"""
        try:
            if hours <= 0 or hours > 8760:  # Max 1 year
                raise HTTPException(status_code=400, detail="Hours must be between 1 and 8760")
            
            metrics = await self.comparison_service.get_repository_metrics(repo, hours)
            automation_score = self.comparison_service._calculate_automation_score(metrics)
            
            # Create a dummy comparison repo for analysis structure
            dummy_metrics = type(metrics)(
                repo_name="baseline",
                total_events=0, workflow_runs=0, deployments=0, pull_requests=0,
                issues=0, commits=0, releases=0, security_events=0,
                last_activity=None, avg_pr_merge_time=None, workflow_success_rate=None
            )
            
            ci_analysis = self.comparison_service._analyze_ci_automation(metrics, dummy_metrics)
            
            return {
                "repository": repo,
                "time_window_hours": hours,
                "generated_at": datetime.now().isoformat(),
                "automation_score": automation_score,
                "ci_analysis": {
                    "workflow_frequency": metrics.workflow_runs / max(metrics.total_events, 1),
                    "deployment_frequency": metrics.deployments / max(metrics.workflow_runs, 1),
                    "security_focus": metrics.security_events / max(metrics.workflow_runs, 1),
                    "success_rate": metrics.workflow_success_rate,
                    "automation_maturity": self._get_maturity_level(automation_score)
                },
                "metrics": {
                    "workflow_runs": metrics.workflow_runs,
                    "deployments": metrics.deployments,
                    "security_events": metrics.security_events,
                    "success_rate": metrics.workflow_success_rate,
                    "releases": metrics.releases
                },
                "recommendations": self._get_ci_recommendations(metrics, automation_score)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing CI automation for {repo}: {e}")
            raise HTTPException(status_code=500, detail=f"CI analysis failed: {str(e)}")
    
    def _get_maturity_level(self, score: float) -> str:
        """Get maturity level based on automation score"""
        if score >= 80:
            return "Advanced"
        elif score >= 60:
            return "Intermediate"
        elif score >= 40:
            return "Basic"
        else:
            return "Minimal"
    
    def _get_ci_recommendations(self, metrics, score: float) -> list[str]:
        """Get CI-specific recommendations"""
        recommendations = []
        
        if score < 40:
            recommendations.append("Implement basic CI workflows for automated testing")
        
        if metrics.workflow_runs == 0:
            recommendations.append("Set up GitHub Actions workflows for continuous integration")
        
        if metrics.deployments == 0:
            recommendations.append("Implement automated deployment workflows")
        
        if metrics.security_events == 0:
            recommendations.append("Add security scanning workflows (CodeQL, dependency scanning)")
        
        if metrics.workflow_success_rate and metrics.workflow_success_rate < 80:
            recommendations.append("Improve workflow reliability - current success rate is below 80%")
        
        if metrics.releases == 0:
            recommendations.append("Consider automated release workflows")
        
        if not recommendations:
            recommendations.append("CI automation is well-established - consider advanced practices like canary deployments")
        
        return recommendations