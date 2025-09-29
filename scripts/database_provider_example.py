#!/usr/bin/env python3
"""
Example script demonstrating database provider switching.

This script shows how to use the same Python interface with different
database backends (SQLite and DynamoDB) following SOLID principles.
"""

import asyncio
import logging
import os
from typing import Dict, Any

from src.github_events_monitor.infrastructure.database_factory import (
    create_database_manager_from_config,
    get_sqlite_manager,
    get_dynamodb_manager,
    get_local_dynamodb_manager
)
from src.github_events_monitor.infrastructure.database_service import DatabaseService
from src.github_events_monitor.enhanced_event_collector import create_enhanced_collector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def demonstrate_sqlite_usage():
    """Demonstrate SQLite database usage."""
    logger.info("=== SQLite Database Provider Demo ===")
    
    # Create SQLite manager
    db_manager = get_sqlite_manager('./demo_sqlite.db')
    db_service = DatabaseService(db_manager)
    
    try:
        # Initialize database
        await db_service.initialize()
        
        # Check health
        health = await db_service.health_check()
        logger.info(f"SQLite Health: {health}")
        
        # Store sample events
        sample_events = [
            {
                'id': 'sqlite_event_1',
                'event_type': 'WatchEvent',
                'repo_name': 'demo/repo',
                'actor_login': 'demo_user',
                'created_at': '2025-01-15T10:00:00Z',
                'payload': {'action': 'started'}
            },
            {
                'id': 'sqlite_event_2',
                'event_type': 'PushEvent',
                'repo_name': 'demo/repo',
                'actor_login': 'demo_user',
                'created_at': '2025-01-15T10:05:00Z',
                'payload': {'commits': [{'sha': 'abc123', 'message': 'Test commit'}]}
            }
        ]
        
        stored_count = await db_service.store_events(sample_events)
        logger.info(f"Stored {stored_count} events in SQLite")
        
        # Query events
        event_counts = await db_service.count_events_by_type(hours_back=24)
        logger.info(f"Event counts: {event_counts}")
        
        # Get repository activity
        activity = await db_service.get_repository_activity('demo/repo', hours_back=24)
        logger.info(f"Repository activity: {activity}")
        
    finally:
        await db_service.close()


async def demonstrate_dynamodb_usage():
    """Demonstrate DynamoDB database usage."""
    logger.info("=== DynamoDB Database Provider Demo ===")
    
    # Create local DynamoDB manager (requires DynamoDB Local running)
    try:
        db_manager = get_local_dynamodb_manager(
            endpoint_url='http://localhost:8000',
            table_prefix='demo-github-events-'
        )
        db_service = DatabaseService(db_manager)
        
        # Initialize database
        await db_service.initialize()
        
        # Check health
        health = await db_service.health_check()
        logger.info(f"DynamoDB Health: {health}")
        
        # Store sample events
        sample_events = [
            {
                'id': 'dynamodb_event_1',
                'event_type': 'WatchEvent',
                'repo_name': 'demo/repo',
                'actor_login': 'demo_user',
                'created_at': '2025-01-15T10:00:00Z',
                'payload': {'action': 'started'}
            },
            {
                'id': 'dynamodb_event_2',
                'event_type': 'PullRequestEvent',
                'repo_name': 'demo/repo',
                'actor_login': 'demo_user',
                'created_at': '2025-01-15T10:05:00Z',
                'payload': {'action': 'opened', 'number': 123}
            }
        ]
        
        stored_count = await db_service.store_events(sample_events)
        logger.info(f"Stored {stored_count} events in DynamoDB")
        
        # Query events
        event_counts = await db_service.count_events_by_type(hours_back=24)
        logger.info(f"Event counts: {event_counts}")
        
        # Get repository activity
        activity = await db_service.get_repository_activity('demo/repo', hours_back=24)
        logger.info(f"Repository activity: {activity}")
        
        await db_service.close()
        
    except Exception as e:
        logger.error(f"DynamoDB demo failed (is DynamoDB Local running?): {e}")


async def demonstrate_enhanced_collector():
    """Demonstrate enhanced collector with different providers."""
    logger.info("=== Enhanced Collector Demo ===")
    
    # SQLite collector
    logger.info("Creating SQLite collector...")
    sqlite_collector = create_enhanced_collector(
        database_config={
            'provider': 'sqlite',
            'db_path': './demo_collector_sqlite.db'
        },
        github_token=os.getenv('GITHUB_TOKEN')
    )
    
    try:
        await sqlite_collector.initialize()
        
        # Test health check
        health = await sqlite_collector.health_check()
        logger.info(f"SQLite Collector Health: {health}")
        
        # Test event fetching (if GitHub token available)
        if os.getenv('GITHUB_TOKEN'):
            logger.info("Fetching events with SQLite collector...")
            stored_count = await sqlite_collector.fetch_and_store_events(limit=5)
            logger.info(f"Stored {stored_count} events")
            
            # Get recent commits
            commits = await sqlite_collector.get_recent_commits('microsoft/vscode', hours=24, limit=5)
            logger.info(f"Found {len(commits)} recent commits")
        
        await sqlite_collector.close()
        
    except Exception as e:
        logger.error(f"SQLite collector demo failed: {e}")
    
    # DynamoDB collector (if available)
    try:
        logger.info("Creating DynamoDB collector...")
        dynamodb_collector = create_enhanced_collector(
            database_config={
                'provider': 'dynamodb',
                'region': 'us-east-1',
                'table_prefix': 'demo-collector-',
                'endpoint_url': 'http://localhost:8000',
                'aws_access_key_id': 'dummy',
                'aws_secret_access_key': 'dummy'
            },
            github_token=os.getenv('GITHUB_TOKEN')
        )
        
        await dynamodb_collector.initialize()
        
        # Test health check
        health = await dynamodb_collector.health_check()
        logger.info(f"DynamoDB Collector Health: {health}")
        
        await dynamodb_collector.close()
        
    except Exception as e:
        logger.error(f"DynamoDB collector demo failed: {e}")


async def demonstrate_provider_switching():
    """Demonstrate seamless switching between database providers."""
    logger.info("=== Provider Switching Demo ===")
    
    # Configuration for different providers
    providers = {
        'sqlite': {
            'provider': 'sqlite',
            'db_path': './demo_switch_sqlite.db'
        },
        'dynamodb_local': {
            'provider': 'dynamodb',
            'region': 'us-east-1',
            'table_prefix': 'switch-demo-',
            'endpoint_url': 'http://localhost:8000',
            'aws_access_key_id': 'dummy',
            'aws_secret_access_key': 'dummy'
        }
    }
    
    sample_events = [
        {
            'id': f'switch_event_{i}',
            'event_type': 'WatchEvent',
            'repo_name': 'demo/switch-repo',
            'actor_login': f'user_{i}',
            'created_at': '2025-01-15T10:00:00Z',
            'payload': {'action': 'started'}
        }
        for i in range(3)
    ]
    
    for provider_name, config in providers.items():
        logger.info(f"Testing provider: {provider_name}")
        
        try:
            # Create database manager
            db_manager = create_database_manager_from_config(config)
            db_service = DatabaseService(db_manager)
            
            # Initialize
            await db_service.initialize()
            
            # Store events
            stored_count = await db_service.store_events(sample_events)
            logger.info(f"  Stored {stored_count} events")
            
            # Query events
            counts = await db_service.count_events_by_type(hours_back=24)
            logger.info(f"  Event counts: {counts}")
            
            # Get activity
            activity = await db_service.get_repository_activity('demo/switch-repo', hours_back=24)
            logger.info(f"  Activity: {activity}")
            
            await db_service.close()
            logger.info(f"  ✅ {provider_name} test completed successfully")
            
        except Exception as e:
            logger.error(f"  ❌ {provider_name} test failed: {e}")


async def main():
    """Main demonstration function."""
    logger.info("GitHub Events Monitor - Database Provider Demonstration")
    logger.info("=" * 60)
    
    # Check if DynamoDB Local is available
    dynamodb_available = False
    try:
        import boto3
        client = boto3.client(
            'dynamodb',
            region_name='us-east-1',
            endpoint_url='http://localhost:8000',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        client.list_tables()
        dynamodb_available = True
        logger.info("✅ DynamoDB Local detected")
    except Exception:
        logger.warning("⚠️  DynamoDB Local not available - skipping DynamoDB demos")
    
    # Run demonstrations
    await demonstrate_sqlite_usage()
    
    if dynamodb_available:
        await demonstrate_dynamodb_usage()
        await demonstrate_provider_switching()
    
    await demonstrate_enhanced_collector()
    
    logger.info("=" * 60)
    logger.info("Demonstration completed!")


if __name__ == "__main__":
    asyncio.run(main())