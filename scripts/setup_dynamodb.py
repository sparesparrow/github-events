#!/usr/bin/env python3
"""
DynamoDB setup script for GitHub Events Monitor.

This script creates and configures DynamoDB tables for the GitHub Events Monitor
with proper indexes and billing configuration.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DynamoDBSetup:
    """DynamoDB setup and configuration manager."""
    
    def __init__(
        self,
        region: str = 'us-east-1',
        table_prefix: str = 'github-events-',
        endpoint_url: Optional[str] = None,
        **aws_credentials
    ):
        self.region = region
        self.table_prefix = table_prefix
        self.endpoint_url = endpoint_url
        
        # Initialize boto3 client
        client_config = {'region_name': region}
        if endpoint_url:
            client_config['endpoint_url'] = endpoint_url
        if aws_credentials:
            client_config.update(aws_credentials)
        
        self.dynamodb = boto3.client('dynamodb', **client_config)
        self.dynamodb_resource = boto3.resource('dynamodb', **client_config)
    
    async def setup_all_tables(self) -> Dict[str, Any]:
        """Set up all required DynamoDB tables."""
        logger.info("Setting up DynamoDB tables...")
        
        table_definitions = [
            self._get_events_table_definition(),
            self._get_commits_table_definition(),
            self._get_commit_files_table_definition(),
            self._get_commit_summaries_table_definition(),
            self._get_repository_health_metrics_table_definition(),
            self._get_developer_metrics_table_definition(),
            self._get_security_metrics_table_definition(),
            self._get_event_patterns_table_definition(),
            self._get_deployment_metrics_table_definition(),
        ]
        
        results = {}
        
        for table_def in table_definitions:
            table_name = table_def['TableName']
            try:
                result = await self._create_table_if_not_exists(table_def)
                results[table_name] = result
            except Exception as e:
                logger.error(f"Failed to create table {table_name}: {e}")
                results[table_name] = {'status': 'failed', 'error': str(e)}
        
        return results
    
    def _get_events_table_definition(self) -> Dict[str, Any]:
        """Get events table definition."""
        return {
            'TableName': f'{self.table_prefix}events',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'repo_name', 'AttributeType': 'S'},
                {'AttributeName': 'event_type', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'},
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'repo-created-index',
                    'KeySchema': [
                        {'AttributeName': 'repo_name', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': 'type-created-index',
                    'KeySchema': [
                        {'AttributeName': 'event_type', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    def _get_commits_table_definition(self) -> Dict[str, Any]:
        """Get commits table definition."""
        return {
            'TableName': f'{self.table_prefix}commits',
            'KeySchema': [
                {'AttributeName': 'sha', 'KeyType': 'HASH'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'sha', 'AttributeType': 'S'},
                {'AttributeName': 'repo_name', 'AttributeType': 'S'},
                {'AttributeName': 'commit_date', 'AttributeType': 'S'},
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'repo-date-index',
                    'KeySchema': [
                        {'AttributeName': 'repo_name', 'KeyType': 'HASH'},
                        {'AttributeName': 'commit_date', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    def _get_commit_files_table_definition(self) -> Dict[str, Any]:
        """Get commit files table definition."""
        return {
            'TableName': f'{self.table_prefix}commit_files',
            'KeySchema': [
                {'AttributeName': 'commit_sha', 'KeyType': 'HASH'},
                {'AttributeName': 'filename', 'KeyType': 'RANGE'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'commit_sha', 'AttributeType': 'S'},
                {'AttributeName': 'filename', 'AttributeType': 'S'},
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    def _get_commit_summaries_table_definition(self) -> Dict[str, Any]:
        """Get commit summaries table definition."""
        return {
            'TableName': f'{self.table_prefix}commit_summaries',
            'KeySchema': [
                {'AttributeName': 'commit_sha', 'KeyType': 'HASH'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'commit_sha', 'AttributeType': 'S'},
                {'AttributeName': 'repo_name', 'AttributeType': 'S'},
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'repo-index',
                    'KeySchema': [
                        {'AttributeName': 'repo_name', 'KeyType': 'HASH'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    def _get_repository_health_metrics_table_definition(self) -> Dict[str, Any]:
        """Get repository health metrics table definition."""
        return {
            'TableName': f'{self.table_prefix}repository_health_metrics',
            'KeySchema': [
                {'AttributeName': 'repo_name', 'KeyType': 'HASH'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'repo_name', 'AttributeType': 'S'},
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    def _get_developer_metrics_table_definition(self) -> Dict[str, Any]:
        """Get developer metrics table definition."""
        return {
            'TableName': f'{self.table_prefix}developer_metrics',
            'KeySchema': [
                {'AttributeName': 'actor_login', 'KeyType': 'HASH'},
                {'AttributeName': 'repo_time_period', 'KeyType': 'RANGE'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'actor_login', 'AttributeType': 'S'},
                {'AttributeName': 'repo_time_period', 'AttributeType': 'S'},
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    def _get_security_metrics_table_definition(self) -> Dict[str, Any]:
        """Get security metrics table definition."""
        return {
            'TableName': f'{self.table_prefix}security_metrics',
            'KeySchema': [
                {'AttributeName': 'repo_name', 'KeyType': 'HASH'},
                {'AttributeName': 'metric_type_date', 'KeyType': 'RANGE'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'repo_name', 'AttributeType': 'S'},
                {'AttributeName': 'metric_type_date', 'AttributeType': 'S'},
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    def _get_event_patterns_table_definition(self) -> Dict[str, Any]:
        """Get event patterns table definition."""
        return {
            'TableName': f'{self.table_prefix}event_patterns',
            'KeySchema': [
                {'AttributeName': 'repo_name', 'KeyType': 'HASH'},
                {'AttributeName': 'event_pattern_detected', 'KeyType': 'RANGE'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'repo_name', 'AttributeType': 'S'},
                {'AttributeName': 'event_pattern_detected', 'AttributeType': 'S'},
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    def _get_deployment_metrics_table_definition(self) -> Dict[str, Any]:
        """Get deployment metrics table definition."""
        return {
            'TableName': f'{self.table_prefix}deployment_metrics',
            'KeySchema': [
                {'AttributeName': 'repo_name', 'KeyType': 'HASH'},
                {'AttributeName': 'deployment_id', 'KeyType': 'RANGE'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'repo_name', 'AttributeType': 'S'},
                {'AttributeName': 'deployment_id', 'AttributeType': 'S'},
            ],
            'BillingMode': 'PAY_PER_REQUEST',
        }
    
    async def _create_table_if_not_exists(self, table_def: Dict[str, Any]) -> Dict[str, Any]:
        """Create a table if it doesn't exist."""
        table_name = table_def['TableName']
        
        try:
            # Check if table exists
            response = self.dynamodb.describe_table(TableName=table_name)
            logger.info(f"Table {table_name} already exists")
            return {
                'status': 'exists',
                'table_name': table_name,
                'table_status': response['Table']['TableStatus']
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                logger.info(f"Creating table {table_name}")
                try:
                    response = self.dynamodb.create_table(**table_def)
                    
                    # Wait for table to be created
                    waiter = self.dynamodb.get_waiter('table_exists')
                    waiter.wait(TableName=table_name)
                    
                    logger.info(f"Table {table_name} created successfully")
                    return {
                        'status': 'created',
                        'table_name': table_name,
                        'table_arn': response['TableDescription']['TableArn']
                    }
                    
                except ClientError as create_error:
                    logger.error(f"Failed to create table {table_name}: {create_error}")
                    return {
                        'status': 'failed',
                        'table_name': table_name,
                        'error': str(create_error)
                    }
            else:
                logger.error(f"Error checking table {table_name}: {e}")
                return {
                    'status': 'error',
                    'table_name': table_name,
                    'error': str(e)
                }
    
    async def delete_all_tables(self) -> Dict[str, Any]:
        """Delete all tables (useful for cleanup/testing)."""
        logger.warning("Deleting all DynamoDB tables...")
        
        try:
            # List all tables with our prefix
            response = self.dynamodb.list_tables()
            tables_to_delete = [
                table for table in response['TableNames'] 
                if table.startswith(self.table_prefix)
            ]
            
            results = {}
            
            for table_name in tables_to_delete:
                try:
                    self.dynamodb.delete_table(TableName=table_name)
                    
                    # Wait for table to be deleted
                    waiter = self.dynamodb.get_waiter('table_not_exists')
                    waiter.wait(TableName=table_name)
                    
                    logger.info(f"Table {table_name} deleted")
                    results[table_name] = {'status': 'deleted'}
                    
                except ClientError as e:
                    logger.error(f"Failed to delete table {table_name}: {e}")
                    results[table_name] = {'status': 'failed', 'error': str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to delete tables: {e}")
            return {'error': str(e)}
    
    async def get_table_info(self) -> Dict[str, Any]:
        """Get information about existing tables."""
        try:
            response = self.dynamodb.list_tables()
            our_tables = [
                table for table in response['TableNames'] 
                if table.startswith(self.table_prefix)
            ]
            
            table_info = {}
            
            for table_name in our_tables:
                try:
                    desc_response = self.dynamodb.describe_table(TableName=table_name)
                    table_desc = desc_response['Table']
                    
                    table_info[table_name] = {
                        'status': table_desc['TableStatus'],
                        'item_count': table_desc.get('ItemCount', 0),
                        'table_size_bytes': table_desc.get('TableSizeBytes', 0),
                        'billing_mode': table_desc.get('BillingModeSummary', {}).get('BillingMode', 'UNKNOWN'),
                        'creation_date': table_desc.get('CreationDateTime', '').isoformat() if table_desc.get('CreationDateTime') else None,
                        'indexes': len(table_desc.get('GlobalSecondaryIndexes', []))
                    }
                    
                except ClientError as e:
                    table_info[table_name] = {'error': str(e)}
            
            return {
                'region': self.region,
                'table_prefix': self.table_prefix,
                'total_tables': len(our_tables),
                'tables': table_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {'error': str(e)}


async def main():
    """Main setup function."""
    import os
    
    # Get configuration from environment
    region = os.getenv('AWS_REGION', 'us-east-1')
    table_prefix = os.getenv('DYNAMODB_TABLE_PREFIX', 'github-events-')
    endpoint_url = os.getenv('DYNAMODB_ENDPOINT_URL')
    
    # AWS credentials (optional, can use IAM roles)
    aws_credentials = {}
    if os.getenv('AWS_ACCESS_KEY_ID'):
        aws_credentials['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID')
    if os.getenv('AWS_SECRET_ACCESS_KEY'):
        aws_credentials['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    setup = DynamoDBSetup(
        region=region,
        table_prefix=table_prefix,
        endpoint_url=endpoint_url,
        **aws_credentials
    )
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'create':
            print("Creating DynamoDB tables...")
            results = await setup.setup_all_tables()
            print(json.dumps(results, indent=2, default=str))
            
        elif command == 'delete':
            print("Deleting DynamoDB tables...")
            results = await setup.delete_all_tables()
            print(json.dumps(results, indent=2, default=str))
            
        elif command == 'info':
            print("Getting table information...")
            info = await setup.get_table_info()
            print(json.dumps(info, indent=2, default=str))
            
        elif command == 'test':
            print("Testing DynamoDB connection...")
            try:
                # Test connection by listing tables
                response = setup.dynamodb.list_tables()
                print(f"✅ Connection successful! Found {len(response['TableNames'])} tables")
                
                # Test table creation with a temporary table
                test_table_def = {
                    'TableName': f'{table_prefix}test-connection',
                    'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
                    'AttributeDefinitions': [{'AttributeName': 'id', 'AttributeType': 'S'}],
                    'BillingMode': 'PAY_PER_REQUEST'
                }
                
                # Create test table
                setup.dynamodb.create_table(**test_table_def)
                waiter = setup.dynamodb.get_waiter('table_exists')
                waiter.wait(TableName=test_table_def['TableName'])
                
                # Delete test table
                setup.dynamodb.delete_table(TableName=test_table_def['TableName'])
                waiter = setup.dynamodb.get_waiter('table_not_exists')
                waiter.wait(TableName=test_table_def['TableName'])
                
                print("✅ Table creation/deletion test successful!")
                
            except Exception as e:
                print(f"❌ Connection test failed: {e}")
                sys.exit(1)
        
        else:
            print(f"Unknown command: {command}")
            print_usage()
            sys.exit(1)
    else:
        print_usage()


def print_usage():
    """Print usage information."""
    print("""
DynamoDB Setup Script for GitHub Events Monitor

Usage:
    python scripts/setup_dynamodb.py <command>

Commands:
    create  - Create all required DynamoDB tables
    delete  - Delete all tables (WARNING: destructive)
    info    - Show information about existing tables
    test    - Test DynamoDB connection and permissions

Environment Variables:
    AWS_REGION                - AWS region (default: us-east-1)
    DYNAMODB_TABLE_PREFIX     - Table name prefix (default: github-events-)
    DYNAMODB_ENDPOINT_URL     - Custom endpoint (for local DynamoDB)
    AWS_ACCESS_KEY_ID         - AWS access key (optional if using IAM)
    AWS_SECRET_ACCESS_KEY     - AWS secret key (optional if using IAM)

Examples:
    # Create tables in AWS
    export AWS_REGION=us-west-2
    export DYNAMODB_TABLE_PREFIX=my-github-events-
    python scripts/setup_dynamodb.py create

    # Test local DynamoDB
    export DYNAMODB_ENDPOINT_URL=http://localhost:8000
    export AWS_ACCESS_KEY_ID=dummy
    export AWS_SECRET_ACCESS_KEY=dummy
    python scripts/setup_dynamodb.py test

    # Get table information
    python scripts/setup_dynamodb.py info
""")


if __name__ == "__main__":
    asyncio.run(main())