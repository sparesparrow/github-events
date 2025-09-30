#!/usr/bin/env python3
"""
Agent Coordination Dashboard

Web dashboard for monitoring and coordinating repository agents
across the sparesparrow ecosystem.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import httpx
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Coordination Dashboard", version="1.0.0")

# Configuration
GITHUB_EVENTS_API_URL = os.getenv('GITHUB_EVENTS_API_URL', 'http://localhost:8080')
TARGET_REPOSITORIES = os.getenv('TARGET_REPOSITORIES', '').split(',')

# Global state
agent_status = {}
last_update = None


async def get_repository_status(repo_name: str) -> Dict[str, Any]:
    """Get status for a specific repository."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get health data
            health_response = await client.get(
                f"{GITHUB_EVENTS_API_URL}/metrics/repository-health",
                params={'repo': repo_name, 'hours': 168}
            )
            
            # Get recent activity
            activity_response = await client.get(
                f"{GITHUB_EVENTS_API_URL}/metrics/repository-activity",
                params={'repo': repo_name, 'hours': 24}
            )
            
            # Get commits
            commits_response = await client.get(
                f"{GITHUB_EVENTS_API_URL}/commits/recent",
                params={'repo': repo_name, 'hours': 24, 'limit': 5}
            )
            
            return {
                'repository': repo_name,
                'health': health_response.json() if health_response.status_code == 200 else {},
                'activity': activity_response.json() if activity_response.status_code == 200 else {},
                'commits': commits_response.json() if commits_response.status_code == 200 else {},
                'status': 'online' if health_response.status_code == 200 else 'offline',
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to get status for {repo_name}: {e}")
        return {
            'repository': repo_name,
            'status': 'error',
            'error': str(e),
            'last_checked': datetime.now(timezone.utc).isoformat()
        }


async def get_agent_results(repo_name: str) -> Dict[str, Any]:
    """Get agent results from shared volume."""
    try:
        results_file = f"/app/data/{repo_name.replace('/', '_')}_agent_results.json"
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                return json.load(f)
        else:
            return {'error': 'No agent results available'}
    except Exception as e:
        return {'error': str(e)}


@app.get("/")
async def dashboard_home():
    """Serve the main dashboard."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent Coordination Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
            .card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .status-excellent {{ border-left: 4px solid #27ae60; }}
            .status-good {{ border-left: 4px solid #f39c12; }}
            .status-needs_attention {{ border-left: 4px solid #e67e22; }}
            .status-critical {{ border-left: 4px solid #e74c3c; }}
            .status-offline {{ border-left: 4px solid #95a5a6; }}
            .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
            .metric-value {{ font-weight: bold; }}
            .refresh-btn {{ background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }}
            .refresh-btn:hover {{ background: #2980b9; }}
            .timestamp {{ color: #7f8c8d; font-size: 0.9em; }}
            .alert {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin: 10px 0; }}
            .alert-high {{ background: #f8d7da; border-color: #f5c6cb; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 Agent Coordination Dashboard</h1>
            <p>Multi-Repository Monitoring for Sparesparrow Ecosystem</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
        </div>
        
        <div id="dashboard-content">
            <p>Loading agent status...</p>
        </div>
        
        <script>
            async function loadDashboardData() {{
                try {{
                    const response = await fetch('/api/dashboard-data');
                    const data = await response.json();
                    renderDashboard(data);
                }} catch (error) {{
                    document.getElementById('dashboard-content').innerHTML = 
                        '<div class="alert alert-high">Error loading dashboard data: ' + error.message + '</div>';
                }}
            }}
            
            function renderDashboard(data) {{
                const content = document.getElementById('dashboard-content');
                let html = '<div class="grid">';
                
                for (const repo of data.repositories) {{
                    const statusClass = `status-${{repo.status}}`;
                    const health = repo.health || {{}};
                    const activity = repo.activity || {{}};
                    const commits = repo.commits || {{}};
                    
                    html += `
                        <div class="card ${{statusClass}}">
                            <h3>${{repo.repository}}</h3>
                            <div class="metric">
                                <span>Status:</span>
                                <span class="metric-value">${{repo.status}}</span>
                            </div>
                            <div class="metric">
                                <span>Health Score:</span>
                                <span class="metric-value">${{health.health_score || 'N/A'}}/100</span>
                            </div>
                            <div class="metric">
                                <span>Recent Commits:</span>
                                <span class="metric-value">${{commits.total_commits || 0}}</span>
                            </div>
                            <div class="metric">
                                <span>Activity (24h):</span>
                                <span class="metric-value">${{activity.total_events || 0}} events</span>
                            </div>
                            <div class="timestamp">Last checked: ${{new Date(repo.last_checked).toLocaleString()}}</div>
                        </div>
                    `;
                }}
                
                html += '</div>';
                
                // Add summary
                html += `
                    <div class="card" style="margin-top: 20px;">
                        <h3>📊 Ecosystem Summary</h3>
                        <div class="metric">
                            <span>Total Repositories:</span>
                            <span class="metric-value">${{data.repositories.length}}</span>
                        </div>
                        <div class="metric">
                            <span>Online Repositories:</span>
                            <span class="metric-value">${{data.repositories.filter(r => r.status === 'online' || r.status === 'excellent' || r.status === 'good').length}}</span>
                        </div>
                        <div class="metric">
                            <span>Repositories Needing Attention:</span>
                            <span class="metric-value">${{data.repositories.filter(r => r.status === 'needs_attention' || r.status === 'critical').length}}</span>
                        </div>
                        <div class="timestamp">Last updated: ${{new Date(data.last_update).toLocaleString()}}</div>
                    </div>
                `;
                
                content.innerHTML = html;
            }}
            
            function refreshData() {{
                loadDashboardData();
            }}
            
            // Auto-refresh every 30 seconds
            setInterval(loadDashboardData, 30000);
            
            // Initial load
            loadDashboardData();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@app.get("/api/dashboard-data")
async def get_dashboard_data():
    """Get dashboard data for all repositories."""
    global last_update
    
    repositories_data = []
    
    for repo in TARGET_REPOSITORIES:
        if repo.strip():
            repo_status = await get_repository_status(repo.strip())
            agent_results = await get_agent_results(repo.strip())
            
            # Combine repository status with agent results
            combined_data = {**repo_status, 'agent_results': agent_results}
            repositories_data.append(combined_data)
    
    last_update = datetime.now(timezone.utc).isoformat()
    
    return {
        'repositories': repositories_data,
        'last_update': last_update,
        'total_repositories': len(repositories_data)
    }


@app.get("/api/repository/{repo_owner}/{repo_name}")
async def get_repository_detail(repo_owner: str, repo_name: str):
    """Get detailed information for a specific repository."""
    repo_full_name = f"{repo_owner}/{repo_name}"
    
    try:
        repo_status = await get_repository_status(repo_full_name)
        agent_results = await get_agent_results(repo_full_name)
        
        return {
            'repository': repo_full_name,
            'status': repo_status,
            'agent_results': agent_results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ecosystem/summary")
async def get_ecosystem_summary():
    """Get summary of the entire ecosystem."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get multi-repository context from GitHub Events API
            response = await client.get(f"{GITHUB_EVENTS_API_URL}/health")
            
            if response.status_code == 200:
                health_data = response.json()
            else:
                health_data = {'error': 'GitHub Events API not available'}
        
        # Get individual repository statuses
        repo_statuses = []
        for repo in TARGET_REPOSITORIES:
            if repo.strip():
                status = await get_repository_status(repo.strip())
                repo_statuses.append(status)
        
        # Calculate ecosystem metrics
        online_repos = len([r for r in repo_statuses if r.get('status') in ['online', 'excellent', 'good']])
        total_events = sum(r.get('activity', {}).get('total_events', 0) for r in repo_statuses)
        avg_health = sum(r.get('health', {}).get('health_score', 0) for r in repo_statuses) / len(repo_statuses) if repo_statuses else 0
        
        return {
            'ecosystem_health': health_data,
            'repository_count': len(TARGET_REPOSITORIES),
            'online_repositories': online_repos,
            'total_events_24h': total_events,
            'average_health_score': round(avg_health, 1),
            'repositories': repo_statuses,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def dashboard_health():
    """Dashboard health check."""
    return {
        'status': 'healthy',
        'dashboard_type': 'agent_coordination',
        'repositories_monitored': len(TARGET_REPOSITORIES),
        'github_events_api': GITHUB_EVENTS_API_URL,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )