"""
Database factory implementation following the Factory pattern.

This module provides a factory for creating database managers based on
the configured provider (SQLite, DynamoDB, etc.), following SOLID principles.
"""

import logging
from typing import Dict, Any, Optional

from .database_interface import DatabaseProvider, DatabaseManager, DatabaseFactory
from .sqlite_adapter import SQLiteConnection, SQLiteManager
from .dynamodb_adapter import DynamoDBConnection, DynamoDBManager

logger = logging.getLogger(__name__)


class ConcreteDatabaseFactory(DatabaseFactory):
    """Concrete implementation of DatabaseFactory."""
    
    @staticmethod
    def create_database_manager(
        provider: DatabaseProvider,
        connection_config: Dict[str, Any]
    ) -> DatabaseManager:
        """Create a database manager for the specified provider."""
        
        if provider == DatabaseProvider.SQLITE:
            return ConcreteDatabaseFactory._create_sqlite_manager(connection_config)
        elif provider == DatabaseProvider.DYNAMODB:
            return ConcreteDatabaseFactory._create_dynamodb_manager(connection_config)
        else:
            raise ValueError(f"Unsupported database provider: {provider}")
    
    @staticmethod
    def _create_sqlite_manager(config: Dict[str, Any]) -> DatabaseManager:
        """Create SQLite database manager."""
        logger.info("Creating SQLite database manager")
        
        # Set default values for SQLite
        sqlite_config = {
            'db_path': config.get('db_path', 'github_events.db'),
            'schema_path': config.get('schema_path', 'database/schema.sql'),
            **config
        }
        
        connection = SQLiteConnection(sqlite_config)
        return SQLiteManager(connection)
    
    @staticmethod
    def _create_dynamodb_manager(config: Dict[str, Any]) -> DatabaseManager:
        """Create DynamoDB database manager."""
        logger.info("Creating DynamoDB database manager")
        
        # Validate required DynamoDB configuration
        required_fields = []  # AWS credentials can come from environment/IAM
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required DynamoDB configuration: {field}")
        
        # Set default values for DynamoDB
        dynamodb_config = {
            'region': config.get('region', 'us-east-1'),
            'table_prefix': config.get('table_prefix', 'github-events-'),
            'endpoint_url': config.get('endpoint_url'),  # For local DynamoDB
            **config
        }
        
        connection = DynamoDBConnection(dynamodb_config)
        return DynamoDBManager(connection)


def create_database_manager_from_config(
    database_config: Dict[str, Any]
) -> DatabaseManager:
    """
    Create database manager from configuration dictionary.
    
    Args:
        database_config: Configuration dictionary containing provider and connection details
        
    Returns:
        DatabaseManager instance
        
    Example:
        # SQLite configuration
        config = {
            'provider': 'sqlite',
            'db_path': './github_events.db'
        }
        
        # DynamoDB configuration
        config = {
            'provider': 'dynamodb',
            'region': 'us-east-1',
            'table_prefix': 'github-events-',
            'aws_access_key_id': 'your_key',
            'aws_secret_access_key': 'your_secret'
        }
    """
    provider_str = database_config.get('provider', 'sqlite').lower()
    
    try:
        provider = DatabaseProvider(provider_str)
    except ValueError:
        raise ValueError(f"Unsupported database provider: {provider_str}")
    
    # Extract connection configuration (excluding provider)
    connection_config = {k: v for k, v in database_config.items() if k != 'provider'}
    
    factory = ConcreteDatabaseFactory()
    return factory.create_database_manager(provider, connection_config)


def create_database_manager_from_env() -> DatabaseManager:
    """
    Create database manager from environment variables.
    
    Environment variables:
        DATABASE_PROVIDER: 'sqlite' or 'dynamodb' (default: sqlite)
        
        For SQLite:
        DATABASE_PATH: Path to SQLite database file
        DATABASE_SCHEMA_PATH: Path to schema SQL file
        
        For DynamoDB:
        AWS_REGION: AWS region (default: us-east-1)
        DYNAMODB_TABLE_PREFIX: Table name prefix (default: github-events-)
        DYNAMODB_ENDPOINT_URL: Custom endpoint URL (for local DynamoDB)
        AWS_ACCESS_KEY_ID: AWS access key
        AWS_SECRET_ACCESS_KEY: AWS secret key
    """
    import os
    
    provider_str = os.getenv('DATABASE_PROVIDER', 'sqlite').lower()
    
    if provider_str == 'sqlite':
        config = {
            'provider': 'sqlite',
            'db_path': os.getenv('DATABASE_PATH', 'github_events.db'),
            'schema_path': os.getenv('DATABASE_SCHEMA_PATH', 'database/schema.sql')
        }
    elif provider_str == 'dynamodb':
        config = {
            'provider': 'dynamodb',
            'region': os.getenv('AWS_REGION', 'us-east-1'),
            'table_prefix': os.getenv('DYNAMODB_TABLE_PREFIX', 'github-events-'),
            'endpoint_url': os.getenv('DYNAMODB_ENDPOINT_URL'),
        }
        
        # Add AWS credentials if provided
        if os.getenv('AWS_ACCESS_KEY_ID'):
            config['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID')
        if os.getenv('AWS_SECRET_ACCESS_KEY'):
            config['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
    else:
        raise ValueError(f"Unsupported DATABASE_PROVIDER: {provider_str}")
    
    return create_database_manager_from_config(config)


class DatabaseManagerSingleton:
    """
    Singleton pattern for database manager to ensure single instance per application.
    
    This is useful for applications that need to share the same database connection
    across multiple components.
    """
    
    _instance: Optional[DatabaseManager] = None
    _config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def get_instance(
        cls, 
        config: Optional[Dict[str, Any]] = None,
        force_recreate: bool = False
    ) -> DatabaseManager:
        """
        Get singleton database manager instance.
        
        Args:
            config: Database configuration (only used on first call or force_recreate)
            force_recreate: Force recreation of the instance
            
        Returns:
            DatabaseManager singleton instance
        """
        if cls._instance is None or force_recreate:
            if config is None:
                # Try to create from environment
                cls._instance = create_database_manager_from_env()
                cls._config = None
            else:
                cls._instance = create_database_manager_from_config(config)
                cls._config = config.copy()
            
            logger.info(f"Created database manager singleton: {type(cls._instance).__name__}")
        
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        if cls._instance:
            # Close existing connection if possible
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(cls._instance.close())
                else:
                    asyncio.run(cls._instance.close())
            except Exception:
                pass
        
        cls._instance = None
        cls._config = None
        logger.info("Reset database manager singleton")


# Convenience functions for common use cases

def get_sqlite_manager(db_path: str = 'github_events.db') -> DatabaseManager:
    """Get SQLite database manager with specified path."""
    config = {
        'provider': 'sqlite',
        'db_path': db_path
    }
    return create_database_manager_from_config(config)


def get_dynamodb_manager(
    region: str = 'us-east-1',
    table_prefix: str = 'github-events-',
    **kwargs
) -> DatabaseManager:
    """Get DynamoDB database manager with specified configuration."""
    config = {
        'provider': 'dynamodb',
        'region': region,
        'table_prefix': table_prefix,
        **kwargs
    }
    return create_database_manager_from_config(config)


def get_local_dynamodb_manager(
    endpoint_url: str = 'http://localhost:8000',
    table_prefix: str = 'github-events-local-'
) -> DatabaseManager:
    """Get DynamoDB database manager configured for local DynamoDB."""
    config = {
        'provider': 'dynamodb',
        'region': 'us-east-1',
        'table_prefix': table_prefix,
        'endpoint_url': endpoint_url,
        'aws_access_key_id': 'dummy',
        'aws_secret_access_key': 'dummy'
    }
    return create_database_manager_from_config(config)