"""
Configuration for GitHub Events Monitor

Centralized configuration management with environment variable support.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
	"""Application configuration"""
	
	# Database settings
	database_provider: str = "sqlite"  # "sqlite" or "dynamodb"
	database_path: str = "github_events.db"
	database_url: Optional[str] = None
	
	# DynamoDB specific settings
	aws_region: str = "us-east-1"
	dynamodb_table_prefix: str = "github-events-"
	dynamodb_endpoint_url: Optional[str] = None  # For local DynamoDB
	aws_access_key_id: Optional[str] = None
	aws_secret_access_key: Optional[str] = None
	
	# GitHub API settings
	github_token: Optional[str] = None
	github_api_base: str = "https://api.github.com"
	user_agent: str = "GitHub-Events-Monitor/1.0"
	
	# Target repositories to monitor
	target_repositories: List[str] = None  # Will be set to ["sparesparrow/mcp-prompts"] in from_env() if not specified
	
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
		# Parse target repositories from environment variable
		target_repos_env = os.getenv("TARGET_REPOSITORIES")
		target_repositories = None
		if target_repos_env:
			target_repositories = [repo.strip() for repo in target_repos_env.split(",") if repo.strip()]
		else:
			# Default target repositories if none specified
			target_repositories = ["sparesparrow/mcp-prompts"]
		
		return cls(
			database_provider=os.getenv("DATABASE_PROVIDER", cls.database_provider),
			database_path=os.getenv("DATABASE_PATH", cls.database_path),
			database_url=os.getenv("DATABASE_URL"),
			aws_region=os.getenv("AWS_REGION", cls.aws_region),
			dynamodb_table_prefix=os.getenv("DYNAMODB_TABLE_PREFIX", cls.dynamodb_table_prefix),
			dynamodb_endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
			aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
			aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
			github_token=os.getenv("GITHUB_TOKEN"),
			github_api_base=os.getenv("GITHUB_API_BASE", cls.github_api_base),
			user_agent=os.getenv("USER_AGENT", cls.user_agent),
			target_repositories=target_repositories,
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
	
	def get_database_url(self) -> str:
		"""Get database URL"""
		if self.database_url:
			return self.database_url
		return f"sqlite:///{self.get_database_path()}"
	
	def get_database_config(self) -> Dict[str, Any]:
		"""Get database configuration for factory"""
		if self.database_provider.lower() == "dynamodb":
			config = {
				'provider': 'dynamodb',
				'region': self.aws_region,
				'table_prefix': self.dynamodb_table_prefix,
			}
			
			if self.dynamodb_endpoint_url:
				config['endpoint_url'] = self.dynamodb_endpoint_url
			
			if self.aws_access_key_id:
				config['aws_access_key_id'] = self.aws_access_key_id
			
			if self.aws_secret_access_key:
				config['aws_secret_access_key'] = self.aws_secret_access_key
			
			return config
		else:
			# Default to SQLite
			return {
				'provider': 'sqlite',
				'db_path': self.get_database_path(),
				'schema_path': 'database/schema.sql'
			}


# Global configuration instance
config = Config.from_env()


