#!/usr/bin/env python3
"""
Repository Agent for Containerized Deployment

This script runs a specialized repository agent in a container,
using GitHub events context for repository-specific operations.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RepositoryAgent:
    """Containerized repository agent with GitHub events context."""
    
    def __init__(self):
        self.target_repository = os.getenv('TARGET_REPOSITORY', 'sparesparrow/ai-servis')
        self.agent_type = os.getenv('AGENT_TYPE', 'general_repository_manager')
        self.github_events_api_url = os.getenv('GITHUB_EVENTS_API_URL', 'http://localhost:8080')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"Repository Agent initialized for {self.target_repository} (type: {self.agent_type})")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def get_repository_context(self) -> Optional[Dict[str, Any]]:
        """Get repository context from GitHub Events API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get repository health
                health_response = await client.get(
                    f"{self.github_events_api_url}/metrics/repository-health",
                    params={'repo': self.target_repository, 'hours': 168}
                )
                
                if health_response.status_code == 200:
                    health_data = health_response.json()
                else:
                    health_data = {'error': f'Health API returned {health_response.status_code}'}
                
                # Get recent commits
                commits_response = await client.get(
                    f"{self.github_events_api_url}/commits/recent",
                    params={'repo': self.target_repository, 'hours': 72, 'limit': 10}
                )
                
                if commits_response.status_code == 200:
                    commits_data = commits_response.json()
                else:
                    commits_data = {'error': f'Commits API returned {commits_response.status_code}'}
                
                # Get security status
                security_response = await client.get(
                    f"{self.github_events_api_url}/metrics/security-monitoring",
                    params={'repo': self.target_repository, 'hours': 168}
                )
                
                if security_response.status_code == 200:
                    security_data = security_response.json()
                else:
                    security_data = {'error': f'Security API returned {security_response.status_code}'}
                
                return {
                    'repository': self.target_repository,
                    'agent_type': self.agent_type,
                    'health': health_data,
                    'recent_commits': commits_data,
                    'security': security_data,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get repository context: {e}")
            return None
    
    async def analyze_repository_status(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze repository status and generate recommendations."""
        analysis = {
            'repository': self.target_repository,
            'agent_type': self.agent_type,
            'status': 'unknown',
            'recommendations': [],
            'alerts': [],
            'actions_required': []
        }
        
        try:
            # Analyze health data
            health = context.get('health', {})
            health_score = health.get('health_score', 0)
            
            if health_score > 80:
                analysis['status'] = 'excellent'
            elif health_score > 60:
                analysis['status'] = 'good'
            elif health_score > 40:
                analysis['status'] = 'needs_attention'
            else:
                analysis['status'] = 'critical'
            
            # Analyze security
            security = context.get('security', {})
            risk_level = security.get('risk_level', 'unknown')
            
            if risk_level == 'high':
                analysis['alerts'].append({
                    'type': 'security',
                    'severity': 'high',
                    'message': 'High security risk detected',
                    'recommendations': security.get('recommendations', [])
                })
                analysis['actions_required'].append('security_review')
            
            # Analyze recent commits
            commits = context.get('recent_commits', {})
            commit_count = commits.get('total_commits', 0)
            
            if commit_count > 0:
                analysis['recommendations'].append(f'Review {commit_count} recent commits')
                
                # Check for high-impact commits
                high_impact_commits = [
                    c for c in commits.get('commits', [])
                    if c.get('summary', {}).get('impact_score', 0) > 80
                ]
                
                if high_impact_commits:
                    analysis['alerts'].append({
                        'type': 'high_impact_commits',
                        'severity': 'medium',
                        'message': f'{len(high_impact_commits)} high-impact commits detected',
                        'commits': [c.get('sha', '')[:8] for c in high_impact_commits]
                    })
                    analysis['actions_required'].append('code_review')
            
            # Agent-type specific analysis
            if self.agent_type == 'prompt_librarian':
                analysis['recommendations'].extend([
                    'Verify prompt catalog integrity',
                    'Check for new prompt templates',
                    'Validate prompt versioning'
                ])
            elif self.agent_type == 'container_manager':
                analysis['recommendations'].extend([
                    'Check container deployment status',
                    'Verify Podman health',
                    'Monitor resource usage'
                ])
            elif self.agent_type == 'ai_service_manager':
                analysis['recommendations'].extend([
                    'Monitor AI service performance',
                    'Check model deployment status',
                    'Validate API endpoints'
                ])
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze repository status: {e}")
            analysis['error'] = str(e)
            return analysis
    
    async def execute_agent_actions(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execute actions based on analysis results."""
        results = {
            'repository': self.target_repository,
            'agent_type': self.agent_type,
            'actions_executed': [],
            'results': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        actions_required = analysis.get('actions_required', [])
        
        for action in actions_required:
            try:
                if action == 'security_review':
                    result = await self._perform_security_review()
                    results['actions_executed'].append('security_review')
                    results['results']['security_review'] = result
                
                elif action == 'code_review':
                    result = await self._perform_code_review()
                    results['actions_executed'].append('code_review')
                    results['results']['code_review'] = result
                
                elif action == 'health_check':
                    result = await self._perform_health_check()
                    results['actions_executed'].append('health_check')
                    results['results']['health_check'] = result
                
            except Exception as e:
                logger.error(f"Failed to execute action {action}: {e}")
                results['results'][action] = {'error': str(e)}
        
        return results
    
    async def _perform_security_review(self) -> Dict[str, Any]:
        """Perform security review for the repository."""
        logger.info(f"Performing security review for {self.target_repository}")
        
        # In a real implementation, this would:
        # 1. Clone the repository
        # 2. Run security scans
        # 3. Analyze security-relevant commits
        # 4. Generate security report
        
        return {
            'status': 'completed',
            'findings': ['Security review completed'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _perform_code_review(self) -> Dict[str, Any]:
        """Perform code review for high-impact commits."""
        logger.info(f"Performing code review for {self.target_repository}")
        
        # In a real implementation, this would:
        # 1. Clone the repository
        # 2. Analyze high-impact commits
        # 3. Run code quality checks
        # 4. Generate review report
        
        return {
            'status': 'completed',
            'findings': ['Code review completed'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform repository health check."""
        logger.info(f"Performing health check for {self.target_repository}")
        
        # Check if repository is accessible
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.github.com/repos/{self.target_repository}")
                if response.status_code == 200:
                    repo_data = response.json()
                    return {
                        'status': 'healthy',
                        'accessible': True,
                        'last_updated': repo_data.get('updated_at'),
                        'default_branch': repo_data.get('default_branch'),
                        'open_issues': repo_data.get('open_issues_count', 0)
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'accessible': False,
                        'error': f'GitHub API returned {response.status_code}'
                    }
        except Exception as e:
            return {
                'status': 'error',
                'accessible': False,
                'error': str(e)
            }
    
    async def run_monitoring_loop(self):
        """Main monitoring loop for the repository agent."""
        logger.info(f"Starting monitoring loop for {self.target_repository}")
        
        iteration = 0
        
        while self.running:
            try:
                iteration += 1
                logger.info(f"Monitoring iteration {iteration} for {self.target_repository}")
                
                # Get repository context
                context = await self.get_repository_context()
                if not context:
                    logger.warning("No repository context available, skipping iteration")
                    await asyncio.sleep(300)  # Wait 5 minutes
                    continue
                
                # Analyze repository status
                analysis = await self.analyze_repository_status(context)
                
                # Execute required actions
                action_results = await self.execute_agent_actions(analysis)
                
                # Log results
                logger.info(f"Iteration {iteration} completed:")
                logger.info(f"  Status: {analysis.get('status')}")
                logger.info(f"  Actions: {len(action_results.get('actions_executed', []))}")
                logger.info(f"  Alerts: {len(analysis.get('alerts', []))}")
                
                # Save results to shared volume for coordination
                results_file = f"/app/data/{self.target_repository.replace('/', '_')}_agent_results.json"
                try:
                    with open(results_file, 'w') as f:
                        json.dump({
                            'context': context,
                            'analysis': analysis,
                            'action_results': action_results,
                            'iteration': iteration,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }, f, indent=2, default=str)
                except Exception as e:
                    logger.error(f"Failed to save results: {e}")
                
                # Wait before next iteration (5 minutes)
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def run(self):
        """Run the repository agent."""
        logger.info(f"Starting Repository Agent for {self.target_repository}")
        
        try:
            # Initial setup and validation
            context = await self.get_repository_context()
            if context:
                logger.info("✅ Repository context successfully retrieved")
                logger.info(f"Health Score: {context.get('health', {}).get('health_score', 'unknown')}")
                logger.info(f"Recent Commits: {context.get('recent_commits', {}).get('total_commits', 0)}")
            else:
                logger.warning("⚠️ Unable to retrieve repository context")
            
            # Start monitoring loop
            await self.run_monitoring_loop()
            
        except Exception as e:
            logger.error(f"Repository agent failed: {e}")
            sys.exit(1)
        
        logger.info("Repository agent shutdown completed")


async def main():
    """Main function."""
    agent = RepositoryAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())