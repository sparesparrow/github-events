"""
GitHub Events Monitor package

Provides:
- FastAPI REST API (see `api.py`)
- MCP server (see `mcp_server.py`)
- Core collector and data access (see `event_collector.py`)
- Utility modules for git operations, GitHub interactions, and merge workflows
"""

__all__ = [
	"api",
	"mcp_server",
	"event_collector",
	"config",
	"utils",
]

__version__ = "1.1.0"



