#!/usr/bin/env python3
"""
GitHub Events MCP Server for Agent Integration

This MCP server provides GitHub events monitoring data as tools for Claude Agent SDK,
enabling agents to use repository context for orchestration and decision making.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

# Import our GitHub events integration
import sys
sys.path.append('/workspace')

from src.github_events_monitor.agent_integration import (
    GitHubEventsAgentIntegration,
    create_sparesparrow_agent_integration,
    GitHubEventsContextProvider
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global integration instance
integration: Optional[GitHubEventsAgentIntegration] = None
context_provider: Optional[GitHubEventsContextProvider] = None


async def initialize_integration():
    """Initialize the GitHub events integration."""
    global integration, context_provider
    
    try:
        integration = await create_sparesparrow_agent_integration()
        context_provider = GitHubEventsContextProvider(integration)
        logger.info("GitHub Events MCP Server initialized")
    except Exception as e:
        logger.error(f"Failed to initialize integration: {e}")
        raise


# Create MCP server
server = Server("github-events-monitor")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available GitHub events monitoring tools."""
    return [
        Tool(
            name="get_repository_context",
            description="Get comprehensive repository context including health, activity, commits, and security status",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo'"
                    },
                    "context_type": {
                        "type": "string",
                        "enum": ["full", "summary", "commits", "security"],
                        "description": "Type of context to retrieve",
                        "default": "full"
                    }
                },
                "required": ["repo_name"]
            }
        ),
        Tool(
            name="get_multi_repository_context",
            description="Get context for multiple repositories for orchestration and workflow planning",
            inputSchema={
                "type": "object",
                "properties": {
                    "repositories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of repository names to analyze"
                    },
                    "include_dependencies": {
                        "type": "boolean",
                        "description": "Include cross-repository dependency analysis",
                        "default": True
                    }
                },
                "required": ["repositories"]
            }
        ),
        Tool(
            name="get_deployment_readiness",
            description="Assess deployment readiness across repositories with recommended deployment order",
            inputSchema={
                "type": "object",
                "properties": {
                    "repositories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of repository names to assess"
                    }
                },
                "required": ["repositories"]
            }
        ),
        Tool(
            name="get_security_alerts",
            description="Get security alerts and recommendations across monitored repositories",
            inputSchema={
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["all", "high", "critical"],
                        "description": "Filter by severity level",
                        "default": "all"
                    }
                }
            }
        ),
        Tool(
            name="get_agent_workflow_context",
            description="Get complete workflow context for agent orchestration including dependencies and coordination metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_type": {
                        "type": "string",
                        "enum": ["deployment", "development", "review", "maintenance"],
                        "description": "Type of workflow context needed",
                        "default": "deployment"
                    }
                }
            }
        ),
        Tool(
            name="generate_claude_agent_config",
            description="Generate Claude Agent SDK configuration for multi-repository orchestration",
            inputSchema={
                "type": "object",
                "properties": {
                    "repositories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Repositories to include in agent configuration"
                    },
                    "include_context_management": {
                        "type": "boolean",
                        "description": "Include context management configuration",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="get_repository_health_summary",
            description="Get health summary for quick repository status overview",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo'"
                    }
                },
                "required": ["repo_name"]
            }
        ),
        Tool(
            name="get_recent_commits_analysis",
            description="Get detailed analysis of recent commits with categorization and impact assessment",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo'"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Hours to look back for commits",
                        "default": 72
                    },
                    "min_impact_score": {
                        "type": "number",
                        "description": "Minimum impact score to include",
                        "default": 0
                    }
                },
                "required": ["repo_name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from agents."""
    if not integration or not context_provider:
        return [TextContent(type="text", text="Error: GitHub Events integration not initialized")]
    
    try:
        if name == "get_repository_context":
            repo_name = arguments["repo_name"]
            context_type = arguments.get("context_type", "full")
            
            context = await context_provider.get_repository_context_for_agent(repo_name, context_type)
            
            return [TextContent(
                type="text",
                text=f"Repository Context for {repo_name}:\n\n{json.dumps(context, indent=2, default=str)}"
            )]
        
        elif name == "get_multi_repository_context":
            repositories = arguments["repositories"]
            include_deps = arguments.get("include_dependencies", True)
            
            contexts = {}
            for repo in repositories:
                contexts[repo] = await context_provider.get_repository_context_for_agent(repo, "summary")
            
            result = {"repositories": contexts}
            
            if include_deps:
                cross_repo_context = await context_provider.get_cross_repository_context()
                result["dependencies"] = cross_repo_context.get("dependencies", {})
                result["deployment_order"] = cross_repo_context.get("deployment_order", [])
            
            return [TextContent(
                type="text",
                text=f"Multi-Repository Context:\n\n{json.dumps(result, indent=2, default=str)}"
            )]
        
        elif name == "get_deployment_readiness":
            repositories = arguments["repositories"]
            
            readiness = {}
            workflow_context = await integration.get_workflow_context()
            
            for repo in repositories:
                repo_context = next((r for r in workflow_context.repositories if r.repo_name == repo), None)
                if repo_context:
                    readiness[repo] = {
                        "ready": repo_context.health_score > 70,
                        "health_score": repo_context.health_score,
                        "activity_level": repo_context.activity_level,
                        "security_risk": repo_context.security_status.get('risk_level', 'unknown'),
                        "recent_commits": len(repo_context.recent_commits),
                        "deployment_priority": workflow_context.deployment_order.index(repo) if repo in workflow_context.deployment_order else 999
                    }
            
            return [TextContent(
                type="text",
                text=f"Deployment Readiness Assessment:\n\n{json.dumps(readiness, indent=2, default=str)}"
            )]
        
        elif name == "get_security_alerts":
            severity = arguments.get("severity", "all")
            
            workflow_context = await integration.get_workflow_context()
            alerts = workflow_context.security_alerts
            
            if severity != "all":
                alerts = [a for a in alerts if a.get('priority') == severity]
            
            return [TextContent(
                type="text",
                text=f"Security Alerts ({severity}):\n\n{json.dumps(alerts, indent=2, default=str)}"
            )]
        
        elif name == "get_agent_workflow_context":
            workflow_type = arguments.get("workflow_type", "deployment")
            
            workflow_context = await integration.get_workflow_context()
            agent_summary = await integration.generate_agent_context_summary()
            
            result = {
                "workflow_type": workflow_type,
                "repositories": len(workflow_context.repositories),
                "deployment_order": workflow_context.deployment_order,
                "security_alerts": len(workflow_context.security_alerts),
                "recommendations": agent_summary.get("agent_recommendations", []),
                "coordination_metadata": workflow_context.coordination_metadata
            }
            
            return [TextContent(
                type="text",
                text=f"Agent Workflow Context ({workflow_type}):\n\n{json.dumps(result, indent=2, default=str)}"
            )]
        
        elif name == "generate_claude_agent_config":
            repositories = arguments["repositories"]
            include_context_mgmt = arguments.get("include_context_management", True)
            
            # Update target repositories
            integration.target_repositories = repositories
            
            # Generate configuration
            orchestrator = MultiRepositoryAgentOrchestrator(integration)
            config = await orchestrator.generate_claude_agent_sdk_config()
            
            if not include_context_mgmt:
                config.pop('context_management', None)
            
            return [TextContent(
                type="text",
                text=f"Claude Agent SDK Configuration:\n\n{json.dumps(config, indent=2, default=str)}"
            )]
        
        elif name == "get_repository_health_summary":
            repo_name = arguments["repo_name"]
            
            repo_context = await integration.get_repository_context(repo_name)
            
            summary = {
                "repository": repo_name,
                "health_score": repo_context.health_score,
                "status": "healthy" if repo_context.health_score > 70 else "needs_attention" if repo_context.health_score > 40 else "critical",
                "activity_level": repo_context.activity_level,
                "recent_commits": len(repo_context.recent_commits),
                "security_risk": repo_context.security_status.get('risk_level', 'unknown'),
                "deployment_ready": repo_context.health_score > 70 and repo_context.security_status.get('risk_level') != 'high',
                "last_updated": repo_context.last_updated.isoformat()
            }
            
            return [TextContent(
                type="text",
                text=f"Repository Health Summary:\n\n{json.dumps(summary, indent=2, default=str)}"
            )]
        
        elif name == "get_recent_commits_analysis":
            repo_name = arguments["repo_name"]
            hours = arguments.get("hours", 72)
            min_impact_score = arguments.get("min_impact_score", 0)
            
            repo_context = await integration.get_repository_context(repo_name)
            
            # Filter commits by impact score
            filtered_commits = [
                c for c in repo_context.recent_commits 
                if c.get('summary', {}).get('impact_score', 0) >= min_impact_score
            ]
            
            analysis = {
                "repository": repo_name,
                "analysis_period_hours": hours,
                "total_commits": len(repo_context.recent_commits),
                "filtered_commits": len(filtered_commits),
                "commits": filtered_commits[:10],  # Limit for context management
                "categories": context_provider._categorize_recent_commits(filtered_commits),
                "high_impact_count": len([c for c in filtered_commits if c.get('summary', {}).get('impact_score', 0) > 80]),
                "security_relevant_count": len([c for c in filtered_commits if c.get('summary', {}).get('security_relevant', False)])
            }
            
            return [TextContent(
                type="text",
                text=f"Recent Commits Analysis:\n\n{json.dumps(analysis, indent=2, default=str)}"
            )]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="github-events://repositories/sparesparrow",
            name="Sparesparrow Repositories Context",
            description="Complete context for all sparesparrow repositories",
            mimeType="application/json"
        ),
        Resource(
            uri="github-events://workflow/deployment-context",
            name="Deployment Workflow Context", 
            description="Context for deployment workflow orchestration",
            mimeType="application/json"
        ),
        Resource(
            uri="github-events://agents/claude-sdk-config",
            name="Claude Agent SDK Configuration",
            description="Generated configuration for Claude Agent SDK",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""
    if not integration:
        return json.dumps({"error": "Integration not initialized"})
    
    try:
        if uri == "github-events://repositories/sparesparrow":
            context = await integration.generate_agent_context_summary()
            return json.dumps(context, indent=2, default=str)
        
        elif uri == "github-events://workflow/deployment-context":
            workflow_context = await integration.get_workflow_context()
            return json.dumps({
                "deployment_order": workflow_context.deployment_order,
                "dependencies": workflow_context.cross_repo_dependencies,
                "security_alerts": workflow_context.security_alerts,
                "coordination_metadata": workflow_context.coordination_metadata
            }, indent=2, default=str)
        
        elif uri == "github-events://agents/claude-sdk-config":
            from src.github_events_monitor.agent_integration import MultiRepositoryAgentOrchestrator
            orchestrator = MultiRepositoryAgentOrchestrator(integration)
            config = await orchestrator.generate_claude_agent_sdk_config()
            return json.dumps(config, indent=2, default=str)
        
        else:
            return json.dumps({"error": f"Unknown resource: {uri}"})
    
    except Exception as e:
        logger.error(f"Failed to read resource {uri}: {e}")
        return json.dumps({"error": str(e)})


async def main():
    """Main MCP server function."""
    # Initialize integration
    await initialize_integration()
    
    # Start MCP server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())