# Create configuration and setup files


from pathlib import Path

# 1. Requirements file
requirements = '''# GitHub Events Monitor Requirements

# Core dependencies
httpx>=0.27.0
aiosqlite>=0.19.0
asyncio-pool>=0.6.0

# FastAPI and web server
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.6.0

# MCP (Model Context Protocol)
mcp>=1.0.0
# Alternative: install from GitHub if not available on PyPI
# git+https://github.com/modelcontextprotocol/python-sdk.git

# Visualization
matplotlib>=3.8.0
Pillow>=10.2.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-mock>=3.12.0
httpx>=0.27.0  # For TestClient

# Development tools
black>=24.0.0
isort>=5.13.0
flake8>=7.0.0
mypy>=1.8.0

# Optional: for better performance
uvloop>=0.19.0; sys_platform != "win32"
'''

# 2. Configuration file
config_py = '''"""
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
'''

# 3. Main entry points
main_api = '''#!/usr/bin/env python3
"""
GitHub Events Monitor - API Server Entry Point
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from github_events_monitor.config import config
from github_events_monitor.api import app


def setup_logging():
    """Setup logging configuration"""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            *([logging.FileHandler(config.log_file)] if config.log_file else [])
        ]
    )


def main():
    """Main entry point for API server"""
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting GitHub Events Monitor API server on {config.api_host}:{config.api_port}")
    logger.info(f"Database path: {config.get_database_path()}")
    logger.info(f"GitHub token configured: {'Yes' if config.github_token else 'No'}")
    
    uvicorn.run(
        "github_events_monitor.api:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_debug,
        log_level=config.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
'''

main_mcp = '''#!/usr/bin/env python3
"""
GitHub Events Monitor - MCP Server Entry Point
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from github_events_monitor.config import config
from github_events_monitor.mcp_server import main as mcp_main


def setup_logging():
    """Setup logging configuration"""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr),  # MCP uses stderr for logs
            *([logging.FileHandler(config.log_file)] if config.log_file else [])
        ]
    )


def main():
    """Main entry point for MCP server"""
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting GitHub Events Monitor MCP server")
    logger.info(f"Database path: {config.get_database_path()}")
    logger.info(f"GitHub token configured: {'Yes' if config.github_token else 'No'}")
    logger.info(f"Transport: {config.mcp_transport}")
    
    # Run the MCP server
    asyncio.run(mcp_main())


if __name__ == "__main__":
    main()
'''

# 4. Test configuration
pytest_ini = '''[tool:pytest]
testpaths = github_events_monitor/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    api: API tests
    mcp: MCP tests
'''

# 5. Environment template
env_template = '''# GitHub Events Monitor Configuration

# GitHub API Settings
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_API_BASE=https://api.github.com
USER_AGENT=GitHub-Events-Monitor/1.0

# Database Settings
DATABASE_PATH=github_events.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/github_events  # For PostgreSQL

# Polling Settings
POLL_INTERVAL=300  # seconds (5 minutes)
MAX_EVENTS_PER_FETCH=  # leave empty for no limit

# API Server Settings
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# MCP Server Settings
MCP_TRANSPORT=stdio  # or http

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=  # leave empty to log only to console

# Cache Settings
ENABLE_CACHING=true
CACHE_TTL=300  # seconds
'''

# 6. Docker configuration
dockerfile = '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV DATABASE_PATH=/app/data/github_events.db
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command (can be overridden)
CMD ["python", "main_api.py"]
'''

docker_compose = '''version: '3.9'

services:
  github-events-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_PATH=/app/data/github_events.db
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: PostgreSQL database
  # postgres:
  #   image: postgres:15
  #   environment:
  #     POSTGRES_DB: github_events
  #     POSTGRES_USER: github_events
  #     POSTGRES_PASSWORD: your_password_here
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"

# volumes:
#   postgres_data:
'''

# Save all configuration files
config_files = {
    "requirements.txt": requirements,
    "github_events_monitor/config.py": config_py,
    "main_api.py": main_api,
    "main_mcp.py": main_mcp,
    "pytest.ini": pytest_ini,
    ".env.template": env_template,
    "Dockerfile": dockerfile,
    "docker-compose.yml": docker_compose
}

for file_path, content in config_files.items():
    # Create directory if needed
    file_path_obj = Path(file_path)
    file_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w") as f:
        f.write(content)

print("✅ Created configuration and setup files:")
for file_path in config_files.keys():
    print(f"   📄 {file_path}")

# Create __init__.py files
init_files = [
    "github_events_monitor/__init__.py",
    "github_events_monitor/tests/__init__.py",
    "github_events_monitor/tests/unit/__init__.py", 
    "github_events_monitor/tests/integration/__init__.py"
]

for init_file in init_files:
    with open(init_file, "w") as f:
        f.write('"""GitHub Events Monitor package"""')

print("\n✅ Created __init__.py files:")
for init_file in init_files:
    print(f"   📄 {init_file}")
