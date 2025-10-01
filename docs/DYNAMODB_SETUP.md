# AWS DynamoDB Setup and Configuration

## Overview

The GitHub Events Monitor now supports AWS DynamoDB as an alternative to SQLite, following SOLID principles with a clean abstraction layer. This allows you to seamlessly switch between SQLite (for development/small deployments) and DynamoDB (for production/scalable deployments) without changing your application code.

## Architecture

### Database Abstraction Layer

The system follows SOLID principles with a clean separation of concerns:

```
Application Layer
    ↓
Database Service (High-level interface)
    ↓
Database Manager (Abstract interface)
    ↓
Database Adapters (SQLite | DynamoDB)
    ↓
Concrete Implementations
```

### Key Components

- **`DatabaseConnection`** - Abstract base for database connections
- **`EventsRepository`** - Abstract interface for events operations
- **`CommitsRepository`** - Abstract interface for commits operations  
- **`MetricsRepository`** - Abstract interface for metrics operations
- **`DatabaseManager`** - Coordinates all repositories
- **`DatabaseFactory`** - Factory pattern for provider selection
- **`DatabaseService`** - High-level service interface

## Configuration

### Environment Variables

Set these environment variables to configure DynamoDB:

```bash
# Database provider selection
export DATABASE_PROVIDER=dynamodb  # or "sqlite"

# AWS Configuration
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key

# DynamoDB specific
export DYNAMODB_TABLE_PREFIX=github-events-
export DYNAMODB_ENDPOINT_URL=http://localhost:8000  # For local DynamoDB

# Alternative: Use IAM roles (recommended for production)
# No need to set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
```

### Configuration Examples

#### Production AWS DynamoDB
```bash
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-west-2
export DYNAMODB_TABLE_PREFIX=prod-github-events-
# Use IAM roles for credentials
```

#### Local DynamoDB Development
```bash
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-east-1
export DYNAMODB_TABLE_PREFIX=local-github-events-
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
```

#### SQLite (Default)
```bash
export DATABASE_PROVIDER=sqlite
export DATABASE_PATH=./github_events.db
```

## DynamoDB Table Schema

### Tables Created

The system creates the following DynamoDB tables:

1. **`{prefix}events`** - GitHub events storage
   - **Primary Key**: `id` (Event ID)
   - **GSI**: `repo-created-index` (repo_name, created_at)
   - **GSI**: `type-created-index` (event_type, created_at)

2. **`{prefix}commits`** - Commit information
   - **Primary Key**: `sha` (Commit SHA)
   - **GSI**: `repo-date-index` (repo_name, commit_date)

3. **`{prefix}commit_files`** - File changes per commit
   - **Primary Key**: `commit_sha`, `filename`

4. **`{prefix}commit_summaries`** - Commit analysis and summaries
   - **Primary Key**: `commit_sha`
   - **GSI**: `repo-index` (repo_name)

5. **`{prefix}repository_health_metrics`** - Repository health scores
   - **Primary Key**: `repo_name`

6. **`{prefix}developer_metrics`** - Developer productivity metrics
   - **Primary Key**: `actor_login`, `repo_time_period`

7. **`{prefix}security_metrics`** - Security monitoring data
   - **Primary Key**: `repo_name`, `metric_type_date`

8. **`{prefix}event_patterns`** - Anomaly detection results
   - **Primary Key**: `repo_name`, `event_pattern_detected`

9. **`{prefix}deployment_metrics`** - Deployment tracking
   - **Primary Key**: `repo_name`, `deployment_id`

### Table Design Principles

- **Pay-per-request billing** - No need to provision capacity
- **Global Secondary Indexes** - Efficient querying patterns
- **Composite sort keys** - Enable complex queries
- **JSON storage** - Flexible payload and metadata storage

## Setup Instructions

### 1. Install Dependencies

```bash
pip install boto3 botocore
# or
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

#### Option A: AWS CLI Configuration
```bash
aws configure
```

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

#### Option C: IAM Roles (Recommended for Production)
- Attach appropriate IAM policies to your EC2 instance, Lambda function, or ECS task
- No need to configure credentials explicitly

### 3. Create DynamoDB Tables

#### Automatic Setup (Recommended)
The tables are created automatically when the application starts:

```bash
export DATABASE_PROVIDER=dynamodb
python -m src.github_events_monitor.api
```

#### Manual Setup
Use the setup script for more control:

```bash
# Test connection
python scripts/setup_dynamodb.py test

# Create all tables
python scripts/setup_dynamodb.py create

# Get table information
python scripts/setup_dynamodb.py info

# Delete all tables (cleanup)
python scripts/setup_dynamodb.py delete
```

### 4. Verify Setup

```bash
# Check application health with DynamoDB
curl http://localhost:8000/health

# Test event collection
curl -X POST http://localhost:8000/collect
```

## Local DynamoDB Development

### Using DynamoDB Local

1. **Download and Start DynamoDB Local:**
```bash
# Download DynamoDB Local
wget https://s3.us-west-2.amazonaws.com/dynamodb-local/dynamodb_local_latest.tar.gz
tar -xzf dynamodb_local_latest.tar.gz

# Start DynamoDB Local
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000
```

2. **Configure Application:**
```bash
export DATABASE_PROVIDER=dynamodb
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export DYNAMODB_TABLE_PREFIX=local-github-events-
```

3. **Setup Tables:**
```bash
python scripts/setup_dynamodb.py create
```

### Using Docker

```bash
# Start DynamoDB Local with Docker
docker run -p 8000:8000 amazon/dynamodb-local

# Configure and setup
export DATABASE_PROVIDER=dynamodb
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
python scripts/setup_dynamodb.py create
```

## Production Deployment

### AWS IAM Permissions

Create an IAM policy with the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchWriteItem",
                "dynamodb:BatchGetItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/github-events-*",
                "arn:aws:dynamodb:*:*:table/github-events-*/index/*"
            ]
        }
    ]
}
```

### Deployment Options

#### 1. EC2 Instance
```bash
# Use IAM instance profile (recommended)
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-west-2
export DYNAMODB_TABLE_PREFIX=prod-github-events-

# Start application
python -m src.github_events_monitor.api
```

#### 2. AWS Lambda
```python
# lambda_function.py
import os
os.environ['DATABASE_PROVIDER'] = 'dynamodb'
os.environ['AWS_REGION'] = 'us-west-2'

from mangum import Mangum
from src.github_events_monitor.api import app

handler = Mangum(app, lifespan="off")
```

#### 3. ECS/Fargate
```yaml
# task-definition.json
{
  "family": "github-events-monitor",
  "taskRoleArn": "arn:aws:iam::account:role/GitHubEventsMonitorRole",
  "containerDefinitions": [
    {
      "name": "github-events-monitor",
      "image": "your-account.dkr.ecr.region.amazonaws.com/github-events-monitor",
      "environment": [
        {"name": "DATABASE_PROVIDER", "value": "dynamodb"},
        {"name": "AWS_REGION", "value": "us-west-2"},
        {"name": "DYNAMODB_TABLE_PREFIX", "value": "prod-github-events-"}
      ]
    }
  ]
}
```

## Performance Considerations

### DynamoDB vs SQLite

| Aspect | SQLite | DynamoDB |
|--------|--------|----------|
| **Scalability** | Single instance | Virtually unlimited |
| **Concurrent Access** | Limited | High concurrency |
| **Operational Overhead** | Low | Managed service |
| **Cost** | Storage only | Pay per request/storage |
| **Setup Complexity** | Simple | Moderate |
| **Query Flexibility** | Full SQL | Limited to key patterns |

### DynamoDB Optimization Tips

1. **Use GSIs Effectively** - Design access patterns around GSIs
2. **Batch Operations** - Use batch write for bulk operations
3. **Avoid Scans** - Prefer queries over scans when possible
4. **Monitor Costs** - Use CloudWatch to track usage
5. **Consider Caching** - Implement caching for frequently accessed data

## Migration Between Providers

### SQLite to DynamoDB

```bash
# 1. Export data from SQLite
python scripts/export_sqlite_data.py > data_export.json

# 2. Configure DynamoDB
export DATABASE_PROVIDER=dynamodb
python scripts/setup_dynamodb.py create

# 3. Import data to DynamoDB
python scripts/import_dynamodb_data.py < data_export.json
```

### DynamoDB to SQLite

```bash
# 1. Export data from DynamoDB
export DATABASE_PROVIDER=dynamodb
python scripts/export_dynamodb_data.py > data_export.json

# 2. Configure SQLite
export DATABASE_PROVIDER=sqlite
python scripts/setup_sqlite.py

# 3. Import data to SQLite
python scripts/import_sqlite_data.py < data_export.json
```

## Monitoring and Troubleshooting

### Health Checks

```bash
# Check database health
curl http://localhost:8000/health

# Expected response for DynamoDB
{
  "status": "ok",
  "database": {
    "status": "healthy",
    "provider": "dynamodb",
    "region": "us-east-1",
    "table_prefix": "github-events-",
    "tables_found": 9
  }
}
```

### Common Issues

#### 1. **Permission Denied**
```
Error: User: arn:aws:iam::account:user/username is not authorized to perform: dynamodb:CreateTable
```
**Solution**: Add DynamoDB permissions to IAM user/role

#### 2. **Table Already Exists**
```
Error: Table already exists: github-events-events
```
**Solution**: This is normal - tables are created once and reused

#### 3. **Rate Limiting**
```
Error: ProvisionedThroughputExceededException
```
**Solution**: Using PAY_PER_REQUEST billing mode avoids this issue

#### 4. **Local DynamoDB Connection Failed**
```
Error: Could not connect to the endpoint URL: "http://localhost:8000"
```
**Solution**: Ensure DynamoDB Local is running on port 8000

### Debugging

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m src.github_events_monitor.api
```

## Cost Optimization

### DynamoDB Pricing Factors

1. **Read/Write Requests** - Pay per request
2. **Storage** - Pay per GB stored
3. **Data Transfer** - Cross-region transfer costs
4. **Backup/Restore** - Optional backup costs

### Cost Optimization Strategies

1. **Use PAY_PER_REQUEST** - No capacity planning needed
2. **Implement TTL** - Auto-delete old data
3. **Optimize Queries** - Use keys and indexes efficiently
4. **Monitor Usage** - Set up CloudWatch alarms
5. **Consider Reserved Capacity** - For predictable workloads

### Estimated Costs

For a typical deployment monitoring 10 repositories:
- **Writes**: ~1,000 events/hour = ~$0.30/month
- **Reads**: ~10,000 queries/hour = ~$1.25/month
- **Storage**: ~1GB data = ~$0.25/month
- **Total**: ~$1.80/month

## Security Best Practices

### IAM Configuration

1. **Principle of Least Privilege** - Grant minimal required permissions
2. **Use IAM Roles** - Avoid hardcoded credentials
3. **Enable CloudTrail** - Audit DynamoDB access
4. **VPC Endpoints** - Keep traffic within AWS network
5. **Encryption** - Enable encryption at rest and in transit

### Example IAM Role

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-west-2:123456789012:table/github-events-*"
            ]
        }
    ]
}
```

## Usage Examples

### Switching Between Providers

#### Use SQLite
```python
from src.github_events_monitor.enhanced_event_collector import create_enhanced_collector

# SQLite configuration
collector = create_enhanced_collector(
    database_config={
        'provider': 'sqlite',
        'db_path': './github_events.db'
    }
)
```

#### Use DynamoDB
```python
# DynamoDB configuration
collector = create_enhanced_collector(
    database_config={
        'provider': 'dynamodb',
        'region': 'us-west-2',
        'table_prefix': 'my-github-events-'
    }
)
```

#### Use Environment Configuration
```python
# Uses DATABASE_PROVIDER environment variable
collector = create_enhanced_collector()
```

### API Usage

The same API endpoints work with both providers:

```bash
# Works with SQLite or DynamoDB
curl "http://localhost:8000/commits/recent?repo=microsoft/vscode&hours=24"
curl "http://localhost:8000/metrics/repository-health?repo=kubernetes/kubernetes"
curl "http://localhost:8000/monitoring/commits?repos=myorg/repo1,myorg/repo2"
```

### MCP Integration

MCP tools work identically with both providers:
```
"Show me recent commits for microsoft/vscode"
"Get repository health for kubernetes/kubernetes"
"Monitor commits across my repositories"
```

## Deployment Scenarios

### Scenario 1: Development (SQLite)
```bash
export DATABASE_PROVIDER=sqlite
export DATABASE_PATH=./dev_github_events.db
python -m src.github_events_monitor.api
```

### Scenario 2: Staging (Local DynamoDB)
```bash
# Start local DynamoDB
docker run -p 8000:8000 amazon/dynamodb-local

# Configure application
export DATABASE_PROVIDER=dynamodb
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
python scripts/setup_dynamodb.py create
python -m src.github_events_monitor.api
```

### Scenario 3: Production (AWS DynamoDB)
```bash
# Configure for production
export DATABASE_PROVIDER=dynamodb
export AWS_REGION=us-west-2
export DYNAMODB_TABLE_PREFIX=prod-github-events-

# Create tables
python scripts/setup_dynamodb.py create

# Start application (uses IAM role for credentials)
python -m src.github_events_monitor.api
```

### Scenario 4: Multi-Environment

```python
# config.py
import os

ENVIRONMENTS = {
    'development': {
        'provider': 'sqlite',
        'db_path': './dev_github_events.db'
    },
    'staging': {
        'provider': 'dynamodb',
        'region': 'us-east-1',
        'table_prefix': 'staging-github-events-',
        'endpoint_url': 'http://localhost:8000'
    },
    'production': {
        'provider': 'dynamodb',
        'region': 'us-west-2',
        'table_prefix': 'prod-github-events-'
    }
}

env = os.getenv('ENVIRONMENT', 'development')
database_config = ENVIRONMENTS[env]
```

## Testing

### Unit Tests

```python
import pytest
from src.github_events_monitor.infrastructure.database_factory import (
    get_sqlite_manager, get_dynamodb_manager
)

@pytest.mark.asyncio
async def test_sqlite_operations():
    manager = get_sqlite_manager(':memory:')
    await manager.initialize()
    
    # Test operations
    events_data = [{'id': 'test1', 'event_type': 'WatchEvent', ...}]
    count = await manager.events.insert_events(events_data)
    assert count == 1

@pytest.mark.asyncio 
async def test_dynamodb_operations():
    # Requires local DynamoDB or AWS credentials
    manager = get_dynamodb_manager(
        endpoint_url='http://localhost:8000',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )
    await manager.initialize()
    
    # Test operations
    events_data = [{'id': 'test1', 'event_type': 'WatchEvent', ...}]
    count = await manager.events.insert_events(events_data)
    assert count == 1
```

### Integration Tests

```bash
# Test with SQLite
export DATABASE_PROVIDER=sqlite
python -m pytest tests/integration/

# Test with local DynamoDB
export DATABASE_PROVIDER=dynamodb
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
python scripts/setup_dynamodb.py create
python -m pytest tests/integration/
```

## Monitoring and Observability

### CloudWatch Metrics

DynamoDB automatically provides CloudWatch metrics:
- **ConsumedReadCapacityUnits**
- **ConsumedWriteCapacityUnits**
- **ItemCount**
- **TableSizeBytes**
- **ThrottledRequests**

### Application Metrics

```bash
# Monitor application health
curl http://localhost:8000/health

# Check specific table health
python scripts/setup_dynamodb.py info
```

### Logging

Enable detailed logging:
```python
import logging
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
```

## Backup and Recovery

### DynamoDB Backup Options

1. **Point-in-Time Recovery** - Continuous backups
2. **On-Demand Backups** - Manual backup creation
3. **Cross-Region Replication** - Disaster recovery

### Enable Point-in-Time Recovery

```bash
aws dynamodb update-continuous-backups \
    --table-name github-events-events \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### Create On-Demand Backup

```bash
aws dynamodb create-backup \
    --table-name github-events-events \
    --backup-name github-events-backup-$(date +%Y%m%d)
```

## Troubleshooting Guide

### Common Error Messages

1. **`ResourceNotFoundException`**
   - **Cause**: Table doesn't exist
   - **Solution**: Run `python scripts/setup_dynamodb.py create`

2. **`ValidationException: Invalid attribute value`**
   - **Cause**: Data type mismatch
   - **Solution**: Check data conversion in adapters

3. **`ProvisionedThroughputExceededException`**
   - **Cause**: Too many requests (shouldn't happen with PAY_PER_REQUEST)
   - **Solution**: Check billing mode configuration

4. **`UnrecognizedClientException`**
   - **Cause**: Invalid AWS credentials
   - **Solution**: Check AWS configuration

### Debug Commands

```bash
# Test DynamoDB connection
python scripts/setup_dynamodb.py test

# List all tables
aws dynamodb list-tables

# Describe specific table
aws dynamodb describe-table --table-name github-events-events

# Check application logs
tail -f logs/github-events-monitor.log
```

## Migration Tools

### Data Export/Import Scripts

Create migration scripts for moving data between providers:

```python
# scripts/migrate_data.py
async def migrate_sqlite_to_dynamodb():
    # Export from SQLite
    sqlite_manager = get_sqlite_manager('./github_events.db')
    
    # Import to DynamoDB
    dynamodb_manager = get_dynamodb_manager(region='us-west-2')
    
    # Migrate events
    events = await sqlite_manager.events.get_events_by_type('WatchEvent', limit=1000)
    await dynamodb_manager.events.insert_events(events)
```

## Conclusion

The DynamoDB integration provides a scalable, managed database solution while maintaining the same Python interface as SQLite. This SOLID approach ensures:

- **Single Responsibility** - Each adapter handles one database type
- **Open/Closed Principle** - Easy to add new database providers
- **Liskov Substitution** - Providers are interchangeable
- **Interface Segregation** - Focused, specific interfaces
- **Dependency Inversion** - Depend on abstractions, not implementations

You can now choose the best database solution for your deployment scenario while keeping the same application code and APIs.