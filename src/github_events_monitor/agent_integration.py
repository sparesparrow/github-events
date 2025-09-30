"""
Agent Integration Layer for GitHub Events Monitor

This module provides integration capabilities for Claude Agent SDK,
allowing agents to use GitHub events data as context for repository orchestration.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

from .infrastructure.database_service import DatabaseService
from .infrastructure.database_factory import create_database_manager_from_config
from .enhanced_event_collector import EnhancedGitHubEventsCollector
from .config import config

logger = logging.getLogger(__name__)


@dataclass
class RepositoryContext:
    """Repository context for agent orchestration."""
    repo_name: str
    health_score: float
    activity_level: str  # 'low', 'medium', 'high'
    recent_commits: List[Dict[str, Any]]
    security_status: Dict[str, Any]
    deployment_status: Dict[str, Any]
    team_activity: Dict[str, Any]
    last_updated: datetime


@dataclass
class AgentWorkflowContext:
    """Context for agent workflow orchestration."""
    repositories: List[RepositoryContext]
    cross_repo_dependencies: Dict[str, List[str]]
    deployment_order: List[str]
    security_alerts: List[Dict[str, Any]]
    coordination_metadata: Dict[str, Any]


class GitHubEventsAgentIntegration:
    """
    Integration layer between GitHub Events Monitor and Claude Agent SDK.
    
    Provides repository context and orchestration capabilities for multi-repo agents.
    """
    
    def __init__(
        self,
        database_config: Optional[Dict[str, Any]] = None,
        target_repositories: Optional[List[str]] = None
    ):
        self.target_repositories = target_repositories or [
            "sparesparrow/mcp-prompts",
            "sparesparrow/mcp-project-orchestrator", 
            "sparesparrow/mcp-router",
            "sparesparrow/podman-desktop-extension-mcp",
            "sparesparrow/ai-servis"
        ]
        
        # Initialize database service
        if database_config:
            db_manager = create_database_manager_from_config(database_config)
            self.db_service = DatabaseService(db_manager)
        else:
            self.db_service = DatabaseService()
        
        self.collector = EnhancedGitHubEventsCollector(
            database_service=self.db_service,
            target_repositories=self.target_repositories
        )
    
    async def initialize(self) -> None:
        """Initialize the agent integration system."""
        await self.collector.initialize()
        logger.info("Agent integration system initialized")
    
    async def get_repository_context(self, repo_name: str) -> RepositoryContext:
        """Get comprehensive repository context for agent decision making."""
        try:
            # Get repository health metrics
            health_data = await self.collector.get_repository_health_score(repo_name, hours=168)
            health_score = health_data.get('health_score', 0)
            
            # Determine activity level
            total_events = health_data.get('total_events', 0)
            if total_events > 50:
                activity_level = 'high'
            elif total_events > 10:
                activity_level = 'medium'
            else:
                activity_level = 'low'
            
            # Get recent commits
            recent_commits = await self.collector.get_recent_commits(repo_name, hours=72, limit=20)
            
            # Get security status
            security_status = await self.collector.get_security_monitoring_report(repo_name, hours=168)
            
            # Get deployment metrics
            deployment_status = await self.collector.get_release_deployment_metrics(repo_name, hours=720)
            
            # Get team activity
            team_activity = await self.collector.get_developer_productivity_metrics(repo_name, hours=168)
            
            return RepositoryContext(
                repo_name=repo_name,
                health_score=health_score,
                activity_level=activity_level,
                recent_commits=recent_commits,
                security_status=security_status,
                deployment_status=deployment_status,
                team_activity=team_activity,
                last_updated=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to get repository context for {repo_name}: {e}")
            # Return minimal context
            return RepositoryContext(
                repo_name=repo_name,
                health_score=0,
                activity_level='unknown',
                recent_commits=[],
                security_status={},
                deployment_status={},
                team_activity={},
                last_updated=datetime.now(timezone.utc)
            )
    
    async def get_workflow_context(self) -> AgentWorkflowContext:
        """Get comprehensive workflow context for agent orchestration."""
        repositories = []
        security_alerts = []
        
        # Collect context for all target repositories
        for repo_name in self.target_repositories:
            repo_context = await self.get_repository_context(repo_name)
            repositories.append(repo_context)
            
            # Check for security alerts
            if repo_context.security_status.get('risk_level') in ['medium', 'high']:
                security_alerts.append({
                    'repo': repo_name,
                    'risk_level': repo_context.security_status.get('risk_level'),
                    'issues': repo_context.security_status.get('recommendations', [])
                })
        
        # Analyze cross-repository dependencies
        cross_repo_deps = await self._analyze_cross_repo_dependencies(repositories)
        
        # Determine deployment order based on dependencies and health
        deployment_order = await self._calculate_deployment_order(repositories, cross_repo_deps)
        
        return AgentWorkflowContext(
            repositories=repositories,
            cross_repo_dependencies=cross_repo_deps,
            deployment_order=deployment_order,
            security_alerts=security_alerts,
            coordination_metadata={
                'total_repositories': len(repositories),
                'healthy_repos': len([r for r in repositories if r.health_score > 70]),
                'active_repos': len([r for r in repositories if r.activity_level in ['medium', 'high']]),
                'last_analysis': datetime.now(timezone.utc).isoformat()
            }
        )
    
    async def _analyze_cross_repo_dependencies(
        self, 
        repositories: List[RepositoryContext]
    ) -> Dict[str, List[str]]:
        """Analyze dependencies between repositories based on commit patterns."""
        dependencies = {}
        
        # Analyze commit timing and patterns to infer dependencies
        for repo in repositories:
            repo_deps = []
            
            # Look for references to other repositories in commit messages
            for commit in repo.recent_commits:
                message = commit.get('message', '').lower()
                for other_repo in self.target_repositories:
                    if other_repo != repo.repo_name:
                        repo_short_name = other_repo.split('/')[-1]
                        if repo_short_name in message or other_repo in message:
                            if other_repo not in repo_deps:
                                repo_deps.append(other_repo)
            
            dependencies[repo.repo_name] = repo_deps
        
        return dependencies
    
    async def _calculate_deployment_order(
        self,
        repositories: List[RepositoryContext],
        dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Calculate optimal deployment order based on dependencies and health."""
        # Sort by health score and dependencies
        repo_scores = {}
        
        for repo in repositories:
            score = repo.health_score
            
            # Boost score for repositories with no dependencies
            if not dependencies.get(repo.repo_name):
                score += 10
            
            # Reduce score for repositories with many dependencies
            score -= len(dependencies.get(repo.repo_name, [])) * 5
            
            repo_scores[repo.repo_name] = score
        
        # Sort by score (highest first for deployment priority)
        return sorted(repo_scores.keys(), key=lambda x: repo_scores[x], reverse=True)
    
    async def generate_agent_context_summary(self) -> Dict[str, Any]:
        """Generate a comprehensive context summary for agent consumption."""
        workflow_context = await self.get_workflow_context()
        
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'monitoring_scope': {
                'repositories': self.target_repositories,
                'total_count': len(self.target_repositories)
            },
            'repository_health': {},
            'deployment_readiness': {},
            'security_overview': {
                'alerts': workflow_context.security_alerts,
                'secure_repos': [],
                'at_risk_repos': []
            },
            'coordination_plan': {
                'deployment_order': workflow_context.deployment_order,
                'dependencies': workflow_context.cross_repo_dependencies
            },
            'agent_recommendations': []
        }
        
        # Process repository data for agent consumption
        for repo in workflow_context.repositories:
            repo_name = repo.repo_name
            
            # Health summary
            summary['repository_health'][repo_name] = {
                'health_score': repo.health_score,
                'activity_level': repo.activity_level,
                'recent_commits_count': len(repo.recent_commits),
                'last_activity': repo.recent_commits[0].get('commit_date') if repo.recent_commits else None
            }
            
            # Deployment readiness
            deployment_ready = (
                repo.health_score > 60 and 
                repo.activity_level != 'low' and
                repo.security_status.get('risk_level', 'high') != 'high'
            )
            
            summary['deployment_readiness'][repo_name] = {
                'ready': deployment_ready,
                'health_score': repo.health_score,
                'security_risk': repo.security_status.get('risk_level', 'unknown'),
                'last_deployment': repo.deployment_status.get('deployments', {}).get('recent_deployments', [{}])[0].get('created_at') if repo.deployment_status.get('deployments', {}).get('recent_deployments') else None
            }
            
            # Security categorization
            risk_level = repo.security_status.get('risk_level', 'unknown')
            if risk_level in ['low', 'medium']:
                summary['security_overview']['secure_repos'].append(repo_name)
            else:
                summary['security_overview']['at_risk_repos'].append(repo_name)
        
        # Generate agent recommendations
        summary['agent_recommendations'] = await self._generate_agent_recommendations(workflow_context)
        
        return summary
    
    async def _generate_agent_recommendations(
        self, 
        workflow_context: AgentWorkflowContext
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for agent actions."""
        recommendations = []
        
        # Analyze each repository for agent actions
        for repo in workflow_context.repositories:
            repo_name = repo.repo_name
            
            # High-impact commits recommendation
            high_impact_commits = [c for c in repo.recent_commits 
                                 if c.get('summary', {}).get('impact_score', 0) > 80]
            if high_impact_commits:
                recommendations.append({
                    'type': 'review_required',
                    'priority': 'high',
                    'repository': repo_name,
                    'action': 'code_review',
                    'description': f'High-impact commits detected in {repo_name}',
                    'details': {
                        'commit_count': len(high_impact_commits),
                        'commits': [c.get('sha', '')[:8] for c in high_impact_commits[:3]]
                    }
                })
            
            # Security alerts recommendation
            if repo.security_status.get('risk_level') == 'high':
                recommendations.append({
                    'type': 'security_alert',
                    'priority': 'critical',
                    'repository': repo_name,
                    'action': 'security_review',
                    'description': f'Security risks detected in {repo_name}',
                    'details': repo.security_status.get('recommendations', [])
                })
            
            # Deployment readiness recommendation
            if (repo.health_score > 80 and 
                repo.deployment_status.get('deployments', {}).get('frequency_per_week', 0) < 1):
                recommendations.append({
                    'type': 'deployment_opportunity',
                    'priority': 'medium',
                    'repository': repo_name,
                    'action': 'deploy',
                    'description': f'{repo_name} is healthy and ready for deployment',
                    'details': {
                        'health_score': repo.health_score,
                        'last_deployment': repo.deployment_status.get('deployments', {}).get('recent_deployments', [{}])[0].get('created_at')
                    }
                })
        
        return sorted(recommendations, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}[x['priority']])


class MultiRepositoryAgentOrchestrator:
    """
    Orchestrator for managing multiple repository agents with GitHub events context.
    
    Integrates with mcp-router, mcp-project-orchestrator, and podman-desktop-extension-mcp
    for comprehensive repository management.
    """
    
    def __init__(self, integration: GitHubEventsAgentIntegration):
        self.integration = integration
        self.active_agents = {}
        self.container_registry = {}
    
    async def create_repository_agent_config(self, repo_name: str) -> Dict[str, Any]:
        """Create agent configuration for a specific repository."""
        repo_context = await self.integration.get_repository_context(repo_name)
        
        # Determine agent specialization based on repository context
        agent_type = self._determine_agent_type(repo_context)
        
        agent_config = {
            'name': f'{repo_name.replace("/", "-")}-agent',
            'description': f'Specialized agent for {repo_name} repository management',
            'repository': repo_name,
            'context': {
                'health_score': repo_context.health_score,
                'activity_level': repo_context.activity_level,
                'security_risk': repo_context.security_status.get('risk_level', 'unknown'),
                'recent_activity': len(repo_context.recent_commits),
                'deployment_ready': repo_context.health_score > 70
            },
            'agent_definition': self._create_agent_definition(repo_name, agent_type, repo_context),
            'container_config': self._create_container_config(repo_name, agent_type),
            'mcp_tools': self._select_mcp_tools(repo_name, agent_type)
        }
        
        return agent_config
    
    def _determine_agent_type(self, repo_context: RepositoryContext) -> str:
        """Determine the type of agent needed based on repository context."""
        repo_name = repo_context.repo_name.lower()
        
        if 'mcp-prompts' in repo_name:
            return 'prompt_librarian'
        elif 'mcp-project-orchestrator' in repo_name:
            return 'project_orchestrator'
        elif 'mcp-router' in repo_name:
            return 'workflow_router'
        elif 'podman-desktop-extension' in repo_name:
            return 'container_manager'
        elif 'ai-servis' in repo_name:
            return 'ai_service_manager'
        else:
            return 'general_repository_manager'
    
    def _create_agent_definition(
        self, 
        repo_name: str, 
        agent_type: str, 
        repo_context: RepositoryContext
    ) -> Dict[str, Any]:
        """Create Claude Agent SDK definition for the repository."""
        
        base_prompt = f"""You are a specialized repository agent for {repo_name}.

Repository Context:
- Health Score: {repo_context.health_score:.1f}/100
- Activity Level: {repo_context.activity_level}
- Recent Commits: {len(repo_context.recent_commits)}
- Security Risk: {repo_context.security_status.get('risk_level', 'unknown')}

Your responsibilities include:
- Monitor repository health and activity
- Coordinate with other repository agents
- Execute deployment and maintenance tasks
- Ensure security and quality standards
"""
        
        agent_definitions = {
            'prompt_librarian': {
                'description': 'Expert in managing prompt templates and catalog operations. Use for prompt-related tasks across repositories.',
                'prompt': base_prompt + """
Specialized Role: Prompt Template Librarian

Expertise:
- Search and manage mcp-prompts catalog using semantic search
- Apply appropriate templates with correct variables
- Maintain prompt versioning and audit trail
- Ensure RBAC compliance for sensitive prompts
- Coordinate prompt usage across multiple repositories

Tools Focus: get_prompt, list_prompts, apply_template, search_prompts
""",
                'tools': ['get_prompt', 'list_prompts', 'apply_template', 'search_prompts', 'Read', 'Grep'],
                'model': 'sonnet'
            },
            
            'project_orchestrator': {
                'description': 'Orchestrates project setup and deployment workflows. Use for complex multi-repo operations.',
                'prompt': base_prompt + """
Specialized Role: Project Orchestration Specialist

Expertise:
- Orchestrate complex multi-repository workflows
- Coordinate deployment sequences based on dependencies
- Manage project scaffolding and template application
- Integrate with CI/CD pipelines
- Monitor cross-repository dependencies

Integration: Works with mcp-project-orchestrator for workflow execution
""",
                'tools': ['Read', 'Write', 'Edit', 'Bash', 'get_prompt', 'apply_template'],
                'model': 'opus'
            },
            
            'workflow_router': {
                'description': 'Routes and coordinates workflows between agents. Use for complex orchestration tasks.',
                'prompt': base_prompt + """
Specialized Role: Workflow Router and Coordinator

Expertise:
- Route requests between specialized agents
- Coordinate complex multi-agent workflows
- Manage agent communication and data flow
- Optimize workflow execution order
- Handle error recovery and fallback strategies

Integration: Central coordinator for mcp-router functionality
""",
                'tools': ['Read', 'Write', 'Bash', 'get_prompt'],
                'model': 'opus'
            },
            
            'container_manager': {
                'description': 'Manages containerized deployments and Podman operations. Use for container orchestration.',
                'prompt': base_prompt + """
Specialized Role: Container and Deployment Manager

Expertise:
- Manage Podman containers and deployments
- Orchestrate containerized service deployments
- Monitor container health and performance
- Handle container networking and volumes
- Integrate with podman-desktop-extension-mcp

Integration: Direct integration with Podman Desktop Extension
""",
                'tools': ['Bash', 'Read', 'Write'],
                'model': 'sonnet'
            },
            
            'ai_service_manager': {
                'description': 'Manages AI service deployments and monitoring. Use for AI/ML service operations.',
                'prompt': base_prompt + """
Specialized Role: AI Service Management Specialist

Expertise:
- Monitor AI service health and performance
- Manage model deployments and updates
- Handle service scaling and optimization
- Monitor API usage and performance metrics
- Coordinate with other services for AI workflows

Focus: Specialized management of AI/ML services and APIs
""",
                'tools': ['Read', 'Write', 'Edit', 'Bash', 'Grep'],
                'model': 'sonnet'
            },
            
            'general_repository_manager': {
                'description': 'General repository management and maintenance. Use for standard repository operations.',
                'prompt': base_prompt + """
Specialized Role: General Repository Manager

Expertise:
- Standard repository maintenance and monitoring
- Code quality and security reviews
- Basic deployment and CI/CD operations
- Issue and PR management
- Documentation maintenance
""",
                'tools': ['Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob'],
                'model': 'sonnet'
            }
        }
        
        return agent_definitions.get(agent_type, agent_definitions['general_repository_manager'])
    
    def _create_container_config(self, repo_name: str, agent_type: str) -> Dict[str, Any]:
        """Create container configuration for repository agent."""
        container_name = f"{repo_name.replace('/', '-')}-agent"
        
        return {
            'container_name': container_name,
            'image': 'github-events-agent:latest',
            'environment': {
                'TARGET_REPOSITORY': repo_name,
                'AGENT_TYPE': agent_type,
                'DATABASE_PROVIDER': 'dynamodb',
                'AWS_REGION': config.aws_region,
                'DYNAMODB_TABLE_PREFIX': config.dynamodb_table_prefix,
                'GITHUB_TOKEN': config.github_token
            },
            'volumes': [
                f'/tmp/{container_name}:/workspace',
                '/var/run/docker.sock:/var/run/docker.sock'  # For container management
            ],
            'network': 'github-events-network',
            'labels': {
                'repository': repo_name,
                'agent_type': agent_type,
                'managed_by': 'github-events-monitor'
            }
        }
    
    def _select_mcp_tools(self, repo_name: str, agent_type: str) -> List[str]:
        """Select appropriate MCP tools for the agent."""
        base_tools = ['github_events_monitor']
        
        if agent_type == 'prompt_librarian':
            return base_tools + ['mcp_prompts']
        elif agent_type == 'project_orchestrator':
            return base_tools + ['mcp_project_orchestrator', 'mcp_prompts']
        elif agent_type == 'workflow_router':
            return base_tools + ['mcp_router', 'mcp_project_orchestrator']
        elif agent_type == 'container_manager':
            return base_tools + ['podman_desktop_extension_mcp']
        else:
            return base_tools
    
    async def generate_claude_agent_sdk_config(self) -> Dict[str, Any]:
        """Generate complete Claude Agent SDK configuration for multi-repo orchestration."""
        workflow_context = await self.integration.get_workflow_context()
        agent_context_summary = await self.integration.generate_agent_context_summary()
        
        # Create agent definitions for each repository
        agents = {}
        
        for repo in workflow_context.repositories:
            agent_config = await self.create_repository_agent_config(repo.repo_name)
            agent_name = agent_config['name']
            agents[agent_name] = agent_config['agent_definition']
        
        # Add orchestrator agent
        agents['multi_repo_orchestrator'] = {
            'description': 'Coordinates operations across multiple repositories. Use for complex multi-repo workflows.',
            'prompt': f"""You are the Multi-Repository Orchestrator.

Current Repository Context:
{json.dumps(agent_context_summary, indent=2)}

Your responsibilities:
- Coordinate operations across {len(self.target_repositories)} repositories
- Use repository-specific agents for specialized tasks
- Manage deployment sequences based on dependencies
- Handle security alerts and compliance
- Optimize workflow execution across repositories

Available Repository Agents:
{', '.join([f"{repo.replace('/', '-')}-agent" for repo in self.target_repositories])}

Deployment Order (recommended):
{' -> '.join(workflow_context.deployment_order)}

Security Alerts: {len(workflow_context.security_alerts)} active
""",
            'tools': ['Read', 'Write', 'Bash', 'get_prompt', 'apply_template'],
            'model': 'opus'
        }
        
        return {
            'agents': agents,
            'context_management': {
                'edits': [
                    {
                        'type': 'clear_tool_uses_20250919',
                        'trigger': {'type': 'input_tokens', 'value': 50000},
                        'keep': {'type': 'tool_uses', 'value': 5},
                        'exclude_tools': ['get_prompt', 'list_prompts', 'github_events_monitor'],
                        'clear_at_least': {'type': 'input_tokens', 'value': 10000}
                    }
                ]
            },
            'metadata': {
                'repositories': self.target_repositories,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'context_summary': agent_context_summary
            }
        }


class GitHubEventsContextProvider:
    """
    Provides GitHub events data as context for Claude Agent SDK.
    
    This class formats repository data for optimal agent consumption,
    managing context size and relevance.
    """
    
    def __init__(self, integration: GitHubEventsAgentIntegration):
        self.integration = integration
    
    async def get_repository_context_for_agent(
        self, 
        repo_name: str,
        context_type: str = 'full'
    ) -> Dict[str, Any]:
        """Get repository context formatted for agent consumption."""
        repo_context = await self.integration.get_repository_context(repo_name)
        
        if context_type == 'summary':
            return {
                'repository': repo_name,
                'health_score': repo_context.health_score,
                'activity_level': repo_context.activity_level,
                'recent_commits_count': len(repo_context.recent_commits),
                'security_risk': repo_context.security_status.get('risk_level', 'unknown'),
                'deployment_ready': repo_context.health_score > 70
            }
        elif context_type == 'commits':
            return {
                'repository': repo_name,
                'recent_commits': repo_context.recent_commits[:10],  # Last 10 commits
                'commit_categories': self._categorize_recent_commits(repo_context.recent_commits)
            }
        elif context_type == 'security':
            return {
                'repository': repo_name,
                'security_status': repo_context.security_status,
                'security_relevant_commits': [
                    c for c in repo_context.recent_commits 
                    if c.get('summary', {}).get('security_relevant', False)
                ]
            }
        else:  # full context
            return {
                'repository': repo_name,
                'health_metrics': {
                    'health_score': repo_context.health_score,
                    'activity_level': repo_context.activity_level
                },
                'recent_commits': repo_context.recent_commits[:5],  # Limit for context size
                'security_status': repo_context.security_status,
                'deployment_status': repo_context.deployment_status,
                'team_activity': repo_context.team_activity[:3] if repo_context.team_activity else [],
                'last_updated': repo_context.last_updated.isoformat()
            }
    
    def _categorize_recent_commits(self, commits: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize recent commits for agent context."""
        categories = {}
        
        for commit in commits:
            commit_categories = commit.get('summary', {}).get('categories', [])
            if isinstance(commit_categories, str):
                try:
                    commit_categories = json.loads(commit_categories)
                except json.JSONDecodeError:
                    commit_categories = []
            
            for category in commit_categories:
                categories[category] = categories.get(category, 0) + 1
        
        return categories
    
    async def get_cross_repository_context(self) -> Dict[str, Any]:
        """Get cross-repository context for orchestration agents."""
        workflow_context = await self.integration.get_workflow_context()
        
        return {
            'repositories': {
                repo.repo_name: {
                    'health_score': repo.health_score,
                    'activity_level': repo.activity_level,
                    'recent_commits': len(repo.recent_commits),
                    'security_risk': repo.security_status.get('risk_level', 'unknown')
                }
                for repo in workflow_context.repositories
            },
            'dependencies': workflow_context.cross_repo_dependencies,
            'deployment_order': workflow_context.deployment_order,
            'security_alerts': workflow_context.security_alerts,
            'coordination_metadata': workflow_context.coordination_metadata
        }


# Factory functions for easy integration
async def create_agent_integration(
    repositories: List[str],
    database_config: Optional[Dict[str, Any]] = None
) -> GitHubEventsAgentIntegration:
    """Create and initialize agent integration for specified repositories."""
    integration = GitHubEventsAgentIntegration(
        database_config=database_config,
        target_repositories=repositories
    )
    await integration.initialize()
    return integration


async def generate_claude_sdk_config_for_repositories(
    repositories: List[str],
    database_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate complete Claude Agent SDK configuration for multiple repositories."""
    integration = await create_agent_integration(repositories, database_config)
    orchestrator = MultiRepositoryAgentOrchestrator(integration)
    
    return await orchestrator.generate_claude_agent_sdk_config()


# Pre-configured integration for sparesparrow repositories
async def create_sparesparrow_agent_integration() -> GitHubEventsAgentIntegration:
    """Create agent integration specifically for sparesparrow repositories."""
    sparesparrow_repos = [
        "sparesparrow/mcp-prompts",
        "sparesparrow/mcp-project-orchestrator", 
        "sparesparrow/mcp-router",
        "sparesparrow/podman-desktop-extension-mcp",
        "sparesparrow/ai-servis"
    ]
    
    # Use DynamoDB for production agent coordination
    db_config = {
        'provider': 'dynamodb',
        'region': 'us-east-1',
        'table_prefix': 'sparesparrow-github-events-'
    }
    
    return await create_agent_integration(sparesparrow_repos, db_config)