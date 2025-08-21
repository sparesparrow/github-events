"""
Configuration for GitHub Events Monitor

Centralized configuration management with environment variable support.
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration"""
    
    # Database settings
    database_path: str = "github_events.db"
    database_url: Optional[str] = None
    
    # GitHub API settings
    github_token: Optional[str] = None
    github_api_base: str = "https://api.github.com"
    user_agent: str = "GitHub-Events-Monitor/1.0"
    
    # Polling settings
    poll_interval_seconds: int = 300  # 5 minutes
    max_events_per_fetch: Optional[int] = None
    
    # API server settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    
    # MCP settings
    mcp_transport: str = "stdio"  # or "http"
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Cache settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls(
            database_path=os.getenv("DATABASE_PATH", cls.database_path),
            database_url=os.getenv("DATABASE_URL"),
            github_token=os.getenv("GITHUB_TOKEN"),
            github_api_base=os.getenv("GITHUB_API_BASE", cls.github_api_base),
            user_agent=os.getenv("USER_AGENT", cls.user_agent),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL", cls.poll_interval_seconds)),
            max_events_per_fetch=int(os.getenv("MAX_EVENTS_PER_FETCH")) if os.getenv("MAX_EVENTS_PER_FETCH") else None,
            api_host=os.getenv("API_HOST", cls.api_host),
            api_port=int(os.getenv("API_PORT", cls.api_port)),
            api_debug=os.getenv("API_DEBUG", "false").lower() == "true",
            mcp_transport=os.getenv("MCP_TRANSPORT", cls.mcp_transport),
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
            log_file=os.getenv("LOG_FILE"),
            enable_caching=os.getenv("ENABLE_CACHING", "true").lower() == "true",
            cache_ttl_seconds=int(os.getenv("CACHE_TTL", cls.cache_ttl_seconds))
        )
    
    def get_database_path(self) -> str:
        """Get absolute database path"""
        if self.database_path.startswith('/'):
            return self.database_path
        return str(Path.cwd() / self.database_path)


# Global configuration instance
config = Config.from_env()
