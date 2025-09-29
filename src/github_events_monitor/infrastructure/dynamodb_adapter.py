"""
AWS DynamoDB adapter implementation following the database interface.

This module provides DynamoDB implementations of the abstract database interfaces,
allowing the GitHub Events Monitor to use DynamoDB as the backend storage.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from boto3.dynamodb.conditions import Key, Attr

from .database_interface import (
    DatabaseConnection, EventsRepository, CommitsRepository, 
    MetricsRepository, DatabaseManager, EventData, CommitData, MetricsData
)

logger = logging.getLogger(__name__)


class DynamoDBConnection(DatabaseConnection):
    """DynamoDB connection implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.region = config.get('region', 'us-east-1')
        self.table_prefix = config.get('table_prefix', 'github-events-')
        self.endpoint_url = config.get('endpoint_url')  # For local DynamoDB
        
        # Initialize boto3 resources
        session_config = {
            'region_name': self.region
        }
        if self.endpoint_url:
            session_config['endpoint_url'] = self.endpoint_url
            
        if 'aws_access_key_id' in config:
            session_config['aws_access_key_id'] = config['aws_access_key_id']
            session_config['aws_secret_access_key'] = config['aws_secret_access_key']
        
        self.session = boto3.Session()
        self.dynamodb = self.session.resource('dynamodb', **session_config)
        self.dynamodb_client = self.session.client('dynamodb', **session_config)
        
        # Table references
        self.tables = {}
        
    async def initialize(self) -> None:
        """Initialize DynamoDB tables."""
        await self._create_tables()
        
    async def _create_tables(self) -> None:
        """Create all required DynamoDB tables."""
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
        
        for table_def in table_definitions:
            await self._create_table_if_not_exists(table_def)
    
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
                    'BillingMode': 'PAY_PER_REQUEST',
                },
                {
                    'IndexName': 'type-created-index',
                    'KeySchema': [
                        {'AttributeName': 'event_type', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST',
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
                    'BillingMode': 'PAY_PER_REQUEST',
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
                    'BillingMode': 'PAY_PER_REQUEST',
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
                {'AttributeName': 'repo_time_period', 'KeyType': 'RANGE'},  # repo_name#time_period#period_start
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
                {'AttributeName': 'metric_type_date', 'KeyType': 'RANGE'},  # metric_type#date
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
                {'AttributeName': 'event_pattern_detected', 'KeyType': 'RANGE'},  # event_type#pattern_type#detected_at
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
    
    async def _create_table_if_not_exists(self, table_def: Dict[str, Any]) -> None:
        """Create a table if it doesn't exist."""
        table_name = table_def['TableName']
        
        try:
            # Check if table exists
            self.dynamodb_client.describe_table(TableName=table_name)
            logger.info(f"Table {table_name} already exists")
            
            # Store table reference
            self.tables[table_name] = self.dynamodb.Table(table_name)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                logger.info(f"Creating table {table_name}")
                try:
                    response = self.dynamodb_client.create_table(**table_def)
                    
                    # Wait for table to be created
                    waiter = self.dynamodb_client.get_waiter('table_exists')
                    waiter.wait(TableName=table_name)
                    
                    logger.info(f"Table {table_name} created successfully")
                    
                    # Store table reference
                    self.tables[table_name] = self.dynamodb.Table(table_name)
                    
                except ClientError as create_error:
                    logger.error(f"Failed to create table {table_name}: {create_error}")
                    raise
            else:
                logger.error(f"Error checking table {table_name}: {e}")
                raise
    
    async def close(self) -> None:
        """Close DynamoDB connection."""
        # DynamoDB doesn't require explicit connection closing
        self.tables.clear()
        logger.info("DynamoDB connection closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check DynamoDB health."""
        try:
            # List tables to verify connection
            response = self.dynamodb_client.list_tables()
            table_count = len([t for t in response['TableNames'] if t.startswith(self.table_prefix)])
            
            return {
                'status': 'healthy',
                'provider': 'dynamodb',
                'region': self.region,
                'table_prefix': self.table_prefix,
                'tables_found': table_count,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'dynamodb',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


class DynamoDBEventsRepository(EventsRepository):
    """DynamoDB implementation of EventsRepository."""
    
    def __init__(self, connection: DynamoDBConnection):
        self.connection = connection
        self.table_name = f'{connection.table_prefix}events'
    
    @property
    def table(self):
        """Get the events table."""
        return self.connection.tables[self.table_name]
    
    async def insert_event(self, event_data: EventData) -> bool:
        """Insert a single event."""
        try:
            # Convert datetime objects to ISO strings
            item = self._prepare_event_item(event_data)
            
            # Use put_item with condition to avoid duplicates
            self.table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(id)'
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # Item already exists
                logger.debug(f"Event {event_data.get('id')} already exists")
                return False
            else:
                logger.error(f"Failed to insert event: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error inserting event: {e}")
            return False
    
    async def insert_events(self, events_data: List[EventData]) -> int:
        """Insert multiple events."""
        inserted_count = 0
        
        # Process in batches of 25 (DynamoDB batch limit)
        batch_size = 25
        for i in range(0, len(events_data), batch_size):
            batch = events_data[i:i + batch_size]
            
            try:
                with self.table.batch_writer() as batch_writer:
                    for event_data in batch:
                        try:
                            item = self._prepare_event_item(event_data)
                            batch_writer.put_item(Item=item)
                            inserted_count += 1
                        except Exception as e:
                            logger.error(f"Failed to prepare event item: {e}")
                            
            except Exception as e:
                logger.error(f"Failed to insert event batch: {e}")
        
        return inserted_count
    
    def _prepare_event_item(self, event_data: EventData) -> Dict[str, Any]:
        """Prepare event data for DynamoDB."""
        item = {}
        
        for key, value in event_data.items():
            if value is not None:
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
                elif isinstance(value, dict):
                    item[key] = json.dumps(value)
                elif isinstance(value, (int, float)):
                    item[key] = Decimal(str(value))
                else:
                    item[key] = str(value)
        
        return item
    
    async def get_events_by_type(
        self, 
        event_type: str,
        repo: Optional[str] = None,
        since_ts: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get events by type with optional filtering."""
        try:
            # Use GSI for efficient querying
            if repo and since_ts:
                # Query by repo and time
                response = self.table.query(
                    IndexName='repo-created-index',
                    KeyConditionExpression=Key('repo_name').eq(repo) & 
                                         Key('created_at').gte(since_ts.isoformat()),
                    FilterExpression=Attr('event_type').eq(event_type),
                    Limit=limit or 1000
                )
            elif since_ts:
                # Query by event type and time
                response = self.table.query(
                    IndexName='type-created-index',
                    KeyConditionExpression=Key('event_type').eq(event_type) & 
                                         Key('created_at').gte(since_ts.isoformat()),
                    Limit=limit or 1000
                )
            else:
                # Scan with filter (less efficient)
                filter_expr = Attr('event_type').eq(event_type)
                if repo:
                    filter_expr = filter_expr & Attr('repo_name').eq(repo)
                
                response = self.table.scan(
                    FilterExpression=filter_expr,
                    Limit=limit or 1000
                )
            
            return [self._convert_item_from_dynamodb(item) for item in response['Items']]
            
        except Exception as e:
            logger.error(f"Failed to get events by type: {e}")
            return []
    
    async def count_events_by_type(
        self, 
        since_ts: Optional[datetime] = None,
        repo: Optional[str] = None
    ) -> Dict[str, int]:
        """Count events by type with optional filtering."""
        try:
            counts = {}
            
            # For DynamoDB, we need to scan/query and aggregate
            filter_expr = None
            if since_ts:
                filter_expr = Attr('created_at').gte(since_ts.isoformat())
            if repo:
                repo_filter = Attr('repo_name').eq(repo)
                filter_expr = repo_filter if filter_expr is None else filter_expr & repo_filter
            
            # Scan the table (could be expensive for large datasets)
            scan_kwargs = {}
            if filter_expr:
                scan_kwargs['FilterExpression'] = filter_expr
            
            response = self.table.scan(**scan_kwargs)
            
            # Count by event type
            for item in response['Items']:
                event_type = item.get('event_type', 'unknown')
                counts[event_type] = counts.get(event_type, 0) + 1
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = self.table.scan(**scan_kwargs)
                
                for item in response['Items']:
                    event_type = item.get('event_type', 'unknown')
                    counts[event_type] = counts.get(event_type, 0) + 1
            
            return counts
            
        except Exception as e:
            logger.error(f"Failed to count events by type: {e}")
            return {}
    
    async def get_trending_repositories(
        self, 
        since_ts: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending repositories based on event activity."""
        try:
            # Scan events since timestamp and aggregate by repository
            response = self.table.scan(
                FilterExpression=Attr('created_at').gte(since_ts.isoformat())
            )
            
            repo_counts = {}
            for item in response['Items']:
                repo_name = item.get('repo_name', 'unknown')
                event_type = item.get('event_type', 'unknown')
                
                if repo_name not in repo_counts:
                    repo_counts[repo_name] = {'total_events': 0, 'event_breakdown': {}}
                
                repo_counts[repo_name]['total_events'] += 1
                repo_counts[repo_name]['event_breakdown'][event_type] = \
                    repo_counts[repo_name]['event_breakdown'].get(event_type, 0) + 1
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression=Attr('created_at').gte(since_ts.isoformat()),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                
                for item in response['Items']:
                    repo_name = item.get('repo_name', 'unknown')
                    event_type = item.get('event_type', 'unknown')
                    
                    if repo_name not in repo_counts:
                        repo_counts[repo_name] = {'total_events': 0, 'event_breakdown': {}}
                    
                    repo_counts[repo_name]['total_events'] += 1
                    repo_counts[repo_name]['event_breakdown'][event_type] = \
                        repo_counts[repo_name]['event_breakdown'].get(event_type, 0) + 1
            
            # Sort by total events and return top repositories
            trending = []
            for repo, data in sorted(repo_counts.items(), 
                                   key=lambda x: x[1]['total_events'], 
                                   reverse=True)[:limit]:
                trending.append({
                    'repo_name': repo,
                    'total_events': data['total_events'],
                    'event_breakdown': data['event_breakdown']
                })
            
            return trending
            
        except Exception as e:
            logger.error(f"Failed to get trending repositories: {e}")
            return []
    
    async def get_repository_activity(
        self, 
        repo: str,
        since_ts: datetime
    ) -> Dict[str, Any]:
        """Get activity summary for a specific repository."""
        try:
            response = self.table.query(
                IndexName='repo-created-index',
                KeyConditionExpression=Key('repo_name').eq(repo) & 
                                     Key('created_at').gte(since_ts.isoformat())
            )
            
            activity = {'total_events': 0, 'event_breakdown': {}}
            
            for item in response['Items']:
                event_type = item.get('event_type', 'unknown')
                activity['total_events'] += 1
                activity['event_breakdown'][event_type] = \
                    activity['event_breakdown'].get(event_type, 0) + 1
            
            return activity
            
        except Exception as e:
            logger.error(f"Failed to get repository activity: {e}")
            return {'total_events': 0, 'event_breakdown': {}}
    
    def _convert_item_from_dynamodb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB item back to standard format."""
        converted = {}
        
        for key, value in item.items():
            if isinstance(value, Decimal):
                # Convert Decimal back to int/float
                converted[key] = int(value) if value % 1 == 0 else float(value)
            elif key == 'payload' and isinstance(value, str):
                # Parse JSON payload
                try:
                    converted[key] = json.loads(value)
                except json.JSONDecodeError:
                    converted[key] = value
            else:
                converted[key] = value
        
        return converted


class DynamoDBCommitsRepository(CommitsRepository):
    """DynamoDB implementation of CommitsRepository."""
    
    def __init__(self, connection: DynamoDBConnection):
        self.connection = connection
        self.commits_table_name = f'{connection.table_prefix}commits'
        self.files_table_name = f'{connection.table_prefix}commit_files'
        self.summaries_table_name = f'{connection.table_prefix}commit_summaries'
    
    @property
    def commits_table(self):
        return self.connection.tables[self.commits_table_name]
    
    @property
    def files_table(self):
        return self.connection.tables[self.files_table_name]
    
    @property
    def summaries_table(self):
        return self.connection.tables[self.summaries_table_name]
    
    async def insert_commit(self, commit_data: CommitData) -> bool:
        """Insert a single commit."""
        try:
            item = self._prepare_commit_item(commit_data)
            self.commits_table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error(f"Failed to insert commit: {e}")
            return False
    
    async def insert_commit_files(
        self, 
        commit_sha: str,
        files_data: List[Dict[str, Any]]
    ) -> int:
        """Insert file changes for a commit."""
        inserted_count = 0
        
        try:
            with self.files_table.batch_writer() as batch_writer:
                for file_data in files_data:
                    try:
                        item = {
                            'commit_sha': commit_sha,
                            'filename': file_data.get('filename', ''),
                            'status': file_data.get('status', ''),
                            'additions': Decimal(str(file_data.get('additions', 0))),
                            'deletions': Decimal(str(file_data.get('deletions', 0))),
                            'changes': Decimal(str(file_data.get('changes', 0))),
                            'patch': file_data.get('patch', ''),
                            'previous_filename': file_data.get('previous_filename', ''),
                            'repo_name': file_data.get('repo_name', ''),
                            'created_at': datetime.now(timezone.utc).isoformat()
                        }
                        batch_writer.put_item(Item=item)
                        inserted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to prepare commit file item: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to insert commit files: {e}")
        
        return inserted_count
    
    async def insert_commit_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Insert commit summary and analysis."""
        try:
            item = self._prepare_summary_item(summary_data)
            self.summaries_table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error(f"Failed to insert commit summary: {e}")
            return False
    
    async def get_commit(self, sha: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get commit by SHA and repository."""
        try:
            response = self.commits_table.get_item(Key={'sha': sha})
            
            if 'Item' in response:
                item = response['Item']
                if item.get('repo_name') == repo:
                    return self._convert_commit_from_dynamodb(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get commit: {e}")
            return None
    
    async def get_commit_files(self, sha: str, repo: str) -> List[Dict[str, Any]]:
        """Get file changes for a commit."""
        try:
            response = self.files_table.query(
                KeyConditionExpression=Key('commit_sha').eq(sha)
            )
            
            files = []
            for item in response['Items']:
                if item.get('repo_name') == repo:
                    files.append(self._convert_file_from_dynamodb(item))
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to get commit files: {e}")
            return []
    
    async def get_recent_commits(
        self, 
        repo: str,
        since_ts: datetime,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent commits for a repository."""
        try:
            response = self.commits_table.query(
                IndexName='repo-date-index',
                KeyConditionExpression=Key('repo_name').eq(repo) & 
                                     Key('commit_date').gte(since_ts.isoformat()),
                ScanIndexForward=False,  # Sort descending
                Limit=limit
            )
            
            commits = []
            for item in response['Items']:
                commit = self._convert_commit_from_dynamodb(item)
                
                # Get summary if available
                try:
                    summary_response = self.summaries_table.get_item(
                        Key={'commit_sha': item['sha']}
                    )
                    if 'Item' in summary_response:
                        commit['summary'] = self._convert_summary_from_dynamodb(
                            summary_response['Item']
                        )
                except Exception:
                    commit['summary'] = None
                
                commits.append(commit)
            
            return commits
            
        except Exception as e:
            logger.error(f"Failed to get recent commits: {e}")
            return []
    
    async def get_commits_by_author(
        self, 
        repo: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get commit statistics grouped by author."""
        try:
            # Query commits for the repository
            response = self.commits_table.query(
                IndexName='repo-date-index',
                KeyConditionExpression=Key('repo_name').eq(repo) & 
                                     Key('commit_date').gte(since_ts.isoformat())
            )
            
            # Group by author
            authors = {}
            for item in response['Items']:
                author = item.get('author_login', 'unknown')
                
                if author not in authors:
                    authors[author] = {
                        'author_login': author,
                        'author_name': item.get('author_name', ''),
                        'commit_count': 0,
                        'total_additions': 0,
                        'total_deletions': 0,
                        'total_files_changed': 0
                    }
                
                authors[author]['commit_count'] += 1
                authors[author]['total_additions'] += int(item.get('stats_additions', 0))
                authors[author]['total_deletions'] += int(item.get('stats_deletions', 0))
                authors[author]['total_files_changed'] += int(item.get('files_changed', 0))
            
            return list(authors.values())
            
        except Exception as e:
            logger.error(f"Failed to get commits by author: {e}")
            return []
    
    async def get_high_impact_commits(
        self, 
        repo: str,
        since_ts: datetime,
        min_impact_score: float = 70.0
    ) -> List[Dict[str, Any]]:
        """Get high-impact commits."""
        try:
            # Query summaries for high impact scores
            response = self.summaries_table.query(
                IndexName='repo-index',
                KeyConditionExpression=Key('repo_name').eq(repo),
                FilterExpression=Attr('impact_score').gte(Decimal(str(min_impact_score)))
            )
            
            high_impact_commits = []
            for summary_item in response['Items']:
                commit_sha = summary_item['commit_sha']
                
                # Get the corresponding commit
                commit_response = self.commits_table.get_item(
                    Key={'sha': commit_sha}
                )
                
                if 'Item' in commit_response:
                    commit_item = commit_response['Item']
                    commit_date = datetime.fromisoformat(
                        commit_item.get('commit_date', '').replace('Z', '+00:00')
                    )
                    
                    if commit_date >= since_ts:
                        commit = self._convert_commit_from_dynamodb(commit_item)
                        commit['summary'] = self._convert_summary_from_dynamodb(summary_item)
                        high_impact_commits.append(commit)
            
            # Sort by impact score descending
            high_impact_commits.sort(
                key=lambda x: x.get('summary', {}).get('impact_score', 0),
                reverse=True
            )
            
            return high_impact_commits
            
        except Exception as e:
            logger.error(f"Failed to get high impact commits: {e}")
            return []
    
    def _prepare_commit_item(self, commit_data: CommitData) -> Dict[str, Any]:
        """Prepare commit data for DynamoDB."""
        item = {}
        
        for key, value in commit_data.items():
            if value is not None:
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
                elif isinstance(value, (int, float)):
                    item[key] = Decimal(str(value))
                elif isinstance(value, bool):
                    item[key] = value
                else:
                    item[key] = str(value)
        
        return item
    
    def _prepare_summary_item(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare summary data for DynamoDB."""
        item = {}
        
        for key, value in summary_data.items():
            if value is not None:
                if isinstance(value, (int, float)):
                    item[key] = Decimal(str(value))
                elif isinstance(value, bool):
                    item[key] = value
                elif isinstance(value, datetime):
                    item[key] = value.isoformat()
                else:
                    item[key] = str(value)
        
        return item
    
    def _convert_commit_from_dynamodb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB commit item to standard format."""
        converted = {}
        
        for key, value in item.items():
            if isinstance(value, Decimal):
                converted[key] = int(value) if value % 1 == 0 else float(value)
            elif key == 'parent_shas' and isinstance(value, str):
                try:
                    converted[key] = json.loads(value)
                except json.JSONDecodeError:
                    converted[key] = []
            else:
                converted[key] = value
        
        return converted
    
    def _convert_file_from_dynamodb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB file item to standard format."""
        converted = {}
        
        for key, value in item.items():
            if isinstance(value, Decimal):
                converted[key] = int(value) if value % 1 == 0 else float(value)
            else:
                converted[key] = value
        
        return converted
    
    def _convert_summary_from_dynamodb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB summary item to standard format."""
        converted = {}
        
        for key, value in item.items():
            if isinstance(value, Decimal):
                converted[key] = int(value) if value % 1 == 0 else float(value)
            elif key == 'change_categories' and isinstance(value, str):
                try:
                    converted[key] = json.loads(value)
                except json.JSONDecodeError:
                    converted[key] = []
            else:
                converted[key] = value
        
        return converted


class DynamoDBMetricsRepository(MetricsRepository):
    """DynamoDB implementation of MetricsRepository."""
    
    def __init__(self, connection: DynamoDBConnection):
        self.connection = connection
        self.health_table_name = f'{connection.table_prefix}repository_health_metrics'
        self.developer_table_name = f'{connection.table_prefix}developer_metrics'
        self.security_table_name = f'{connection.table_prefix}security_metrics'
    
    @property
    def health_table(self):
        return self.connection.tables[self.health_table_name]
    
    @property
    def developer_table(self):
        return self.connection.tables[self.developer_table_name]
    
    @property
    def security_table(self):
        return self.connection.tables[self.security_table_name]
    
    async def upsert_repository_health_metrics(self, metrics_data: MetricsData) -> bool:
        """Insert or update repository health metrics."""
        try:
            item = self._prepare_metrics_item(metrics_data)
            self.health_table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert repository health metrics: {e}")
            return False
    
    async def get_repository_health_metrics(self, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository health metrics."""
        try:
            response = self.health_table.get_item(Key={'repo_name': repo})
            
            if 'Item' in response:
                return self._convert_metrics_from_dynamodb(response['Item'])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get repository health metrics: {e}")
            return None
    
    async def upsert_developer_metrics(self, metrics_data: MetricsData) -> bool:
        """Insert or update developer metrics."""
        try:
            # Create composite sort key
            repo_time_period = f"{metrics_data['repo_name']}#{metrics_data['time_period']}#{metrics_data['period_start']}"
            
            item = self._prepare_metrics_item(metrics_data)
            item['repo_time_period'] = repo_time_period
            
            self.developer_table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert developer metrics: {e}")
            return False
    
    async def get_developer_metrics(
        self, 
        repo: str,
        time_period: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get developer metrics."""
        try:
            # Query by actor_login (we'd need to scan for repo filtering)
            response = self.developer_table.scan(
                FilterExpression=Attr('repo_name').eq(repo) & 
                               Attr('time_period').eq(time_period) &
                               Attr('period_start').gte(since_ts.isoformat())
            )
            
            return [self._convert_metrics_from_dynamodb(item) for item in response['Items']]
            
        except Exception as e:
            logger.error(f"Failed to get developer metrics: {e}")
            return []
    
    async def upsert_security_metrics(self, metrics_data: MetricsData) -> bool:
        """Insert or update security metrics."""
        try:
            # Create composite sort key
            metric_type_date = f"{metrics_data['metric_type']}#{metrics_data['date']}"
            
            item = self._prepare_metrics_item(metrics_data)
            item['metric_type_date'] = metric_type_date
            
            self.security_table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert security metrics: {e}")
            return False
    
    async def get_security_metrics(
        self, 
        repo: str,
        since_ts: datetime
    ) -> List[Dict[str, Any]]:
        """Get security metrics."""
        try:
            response = self.security_table.query(
                KeyConditionExpression=Key('repo_name').eq(repo),
                FilterExpression=Attr('date').gte(since_ts.date().isoformat())
            )
            
            return [self._convert_metrics_from_dynamodb(item) for item in response['Items']]
            
        except Exception as e:
            logger.error(f"Failed to get security metrics: {e}")
            return []
    
    def _prepare_metrics_item(self, metrics_data: MetricsData) -> Dict[str, Any]:
        """Prepare metrics data for DynamoDB."""
        item = {}
        
        for key, value in metrics_data.items():
            if value is not None:
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
                elif isinstance(value, (int, float)):
                    item[key] = Decimal(str(value))
                elif isinstance(value, bool):
                    item[key] = value
                elif isinstance(value, (list, dict)):
                    item[key] = json.dumps(value)
                else:
                    item[key] = str(value)
        
        return item
    
    def _convert_metrics_from_dynamodb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB metrics item to standard format."""
        converted = {}
        
        for key, value in item.items():
            if isinstance(value, Decimal):
                converted[key] = int(value) if value % 1 == 0 else float(value)
            elif isinstance(value, str) and key.endswith('_json'):
                try:
                    converted[key.replace('_json', '')] = json.loads(value)
                except json.JSONDecodeError:
                    converted[key] = value
            else:
                converted[key] = value
        
        return converted


class DynamoDBManager(DatabaseManager):
    """DynamoDB implementation of DatabaseManager."""
    
    def __init__(self, connection: DynamoDBConnection):
        super().__init__(connection)
        self._events = DynamoDBEventsRepository(connection)
        self._commits = DynamoDBCommitsRepository(connection)
        self._metrics = DynamoDBMetricsRepository(connection)
    
    @property
    def events(self) -> EventsRepository:
        """Get events repository."""
        return self._events
    
    @property
    def commits(self) -> CommitsRepository:
        """Get commits repository."""
        return self._commits
    
    @property
    def metrics(self) -> MetricsRepository:
        """Get metrics repository."""
        return self._metrics