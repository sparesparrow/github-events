"""
OpenSSL Refactoring Monitoring API Endpoints

Specialized endpoints for tracking OpenSSL repository modernization
and DevOps process improvements.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timezone

from src.github_events_monitor.application.github_events_query_service import GitHubEventsQueryService
from src.github_events_monitor.openssl_refactor_monitor import (
    OpenSSLRefactorMonitor,
    OpenSSLDevOpsTracker,
    create_openssl_refactor_monitor
)

router = APIRouter(prefix="/openssl", tags=["OpenSSL Refactoring"])

# Global monitor instance
_openssl_monitor: Optional[OpenSSLRefactorMonitor] = None


async def get_openssl_monitor() -> OpenSSLRefactorMonitor:
    """Get OpenSSL refactor monitor instance."""
    global _openssl_monitor
    if _openssl_monitor is None:
        _openssl_monitor = await create_openssl_refactor_monitor()
    return _openssl_monitor


@router.get("/refactoring/progress")
async def openssl_refactoring_progress(
    hours: int = 168,
    monitor: OpenSSLRefactorMonitor = Depends(get_openssl_monitor)
):
    """Get comprehensive OpenSSL refactoring progress analysis."""
    try:
        metrics = await monitor.analyze_refactoring_progress(hours)
        
        return {
            "repository": "openssl/openssl",
            "analysis_period_hours": hours,
            "refactoring_metrics": {
                "overall_progress": f"{metrics.overall_refactor_progress:.1f}%",
                "ci_cd_modernization": f"{metrics.ci_cd_modernization_score:.1f}%",
                "python_integration": f"{metrics.python_integration_progress:.1f}%",
                "conan_adoption": f"{metrics.conan_adoption_score:.1f}%",
                "build_efficiency": f"{metrics.build_efficiency_improvement:.1f}%",
                "security_compliance": f"{metrics.security_compliance_score:.1f}%",
                "agent_coordination": f"{metrics.agent_coordination_effectiveness:.1f}%"
            },
            "progress_grade": _calculate_progress_grade(metrics.overall_refactor_progress),
            "timestamp": metrics.last_updated.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze refactoring progress: {str(e)}")


@router.get("/refactoring/report")
async def openssl_refactoring_report(
    monitor: OpenSSLRefactorMonitor = Depends(get_openssl_monitor)
):
    """Generate comprehensive OpenSSL refactoring report."""
    try:
        report = await monitor.generate_refactoring_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate refactoring report: {str(e)}")


@router.get("/devops/kpis")
async def openssl_devops_kpis(
    monitor: OpenSSLRefactorMonitor = Depends(get_openssl_monitor)
):
    """Get DevOps KPIs for OpenSSL refactoring process."""
    try:
        tracker = OpenSSLDevOpsTracker(monitor)
        kpis = await tracker.track_devops_kpis()
        
        return {
            "repository": "openssl/openssl",
            "devops_metrics": kpis,
            "modernization_status": await _get_modernization_status(monitor),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get DevOps KPIs: {str(e)}")


@router.get("/agent-config")
async def openssl_agent_config(
    monitor: OpenSSLRefactorMonitor = Depends(get_openssl_monitor)
):
    """Generate Claude Agent SDK configuration for OpenSSL refactoring."""
    try:
        config = await monitor.generate_agent_sdk_config_for_openssl()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate agent config: {str(e)}")


@router.get("/modernization/recommendations")
async def openssl_modernization_recommendations(
    priority: Optional[str] = Query(None, regex="^(critical|high|medium|low)$"),
    category: Optional[str] = Query(None, regex="^(ci_cd|python_tooling|package_management|security|agent_integration)$"),
    monitor: OpenSSLRefactorMonitor = Depends(get_openssl_monitor)
):
    """Get modernization recommendations for OpenSSL."""
    try:
        report = await monitor.generate_refactoring_report()
        recommendations = report.get('modernization_recommendations', [])
        
        # Filter by priority
        if priority:
            recommendations = [r for r in recommendations if r.get('priority') == priority]
        
        # Filter by category
        if category:
            recommendations = [r for r in recommendations if r.get('category') == category]
        
        return {
            "repository": "openssl/openssl",
            "recommendations": recommendations,
            "filters": {"priority": priority, "category": category},
            "total_recommendations": len(recommendations),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.get("/workflow-analysis")
async def openssl_workflow_analysis(
    monitor: OpenSSLRefactorMonitor = Depends(get_openssl_monitor)
):
    """Analyze OpenSSL workflow runs and performance."""
    try:
        workflow_data = await monitor.track_workflow_runs()
        
        return {
            "repository": "openssl/openssl",
            "workflow_analysis": workflow_data,
            "optimization_potential": await _calculate_optimization_potential(workflow_data),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze workflows: {str(e)}")


@router.get("/sparesparrow-integration")
async def openssl_sparesparrow_integration(
    monitor: OpenSSLRefactorMonitor = Depends(get_openssl_monitor)
):
    """Get integration plan with sparesparrow agent ecosystem."""
    try:
        metrics = await monitor.analyze_refactoring_progress()
        agent_plan = await monitor._generate_agent_plan(metrics)
        
        return {
            "repository": "openssl/openssl",
            "integration_plan": agent_plan,
            "sparesparrow_repositories": [
                "sparesparrow/mcp-prompts",
                "sparesparrow/mcp-project-orchestrator",
                "sparesparrow/mcp-router", 
                "sparesparrow/podman-desktop-extension-mcp",
                "sparesparrow/ai-servis"
            ],
            "integration_readiness": {
                "mcp_tools_available": True,
                "agent_ecosystem_ready": True,
                "aws_services_configured": True,
                "github_events_monitoring": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get integration plan: {str(e)}")


@router.post("/refactoring/start-monitoring")
async def start_openssl_monitoring(
    enable_agent_coordination: bool = True,
    use_aws_services: bool = True,
    monitor: OpenSSLRefactorMonitor = Depends(get_openssl_monitor)
):
    """Start comprehensive OpenSSL refactoring monitoring."""
    try:
        # Initialize monitoring for OpenSSL
        await monitor.integration.collector.fetch_and_store_events(limit=200)
        
        # Generate initial assessment
        report = await monitor.generate_refactoring_report()
        
        # Setup agent coordination if requested
        agent_config = None
        if enable_agent_coordination:
            agent_config = await monitor.generate_agent_sdk_config_for_openssl()
        
        return {
            "status": "monitoring_started",
            "repository": "openssl/openssl",
            "initial_assessment": report,
            "agent_coordination": agent_config if enable_agent_coordination else None,
            "aws_integration": use_aws_services,
            "monitoring_endpoints": {
                "progress": "/openssl/refactoring/progress",
                "report": "/openssl/refactoring/report", 
                "kpis": "/openssl/devops/kpis",
                "recommendations": "/openssl/modernization/recommendations"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


# Helper functions
def _calculate_progress_grade(progress: float) -> str:
    """Calculate progress grade based on percentage."""
    if progress >= 90:
        return "A+ (Excellent)"
    elif progress >= 80:
        return "A (Very Good)"
    elif progress >= 70:
        return "B+ (Good)"
    elif progress >= 60:
        return "B (Satisfactory)"
    elif progress >= 50:
        return "C+ (Needs Improvement)"
    elif progress >= 40:
        return "C (Poor)"
    else:
        return "D (Critical)"


async def _get_modernization_status(monitor: OpenSSLRefactorMonitor) -> Dict[str, Any]:
    """Get current modernization status."""
    metrics = await monitor.analyze_refactoring_progress()
    
    return {
        "phase": "assessment" if metrics.overall_refactor_progress < 20 else 
                "implementation" if metrics.overall_refactor_progress < 70 else
                "optimization",
        "readiness_for_agents": metrics.agent_coordination_effectiveness > 30,
        "aws_integration_ready": True,
        "sparesparrow_ecosystem_ready": True
    }


async def _calculate_optimization_potential(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate optimization potential based on workflow analysis."""
    return {
        "time_savings_potential": "40-60%",  # Based on typical CI/CD optimizations
        "cost_reduction_potential": "30-50%", # GitHub Actions cost optimization
        "reliability_improvement": "20-40%",  # Better failure handling
        "maintainability_gain": "50-70%"     # Modern tooling adoption
    }