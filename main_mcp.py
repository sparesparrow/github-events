#!/usr/bin/env python3
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
