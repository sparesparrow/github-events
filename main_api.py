#!/usr/bin/env python3
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
