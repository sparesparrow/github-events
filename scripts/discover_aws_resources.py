#!/usr/bin/env python3
"""
AWS Resource Discovery for GitHub Events Monitor

This script attempts to discover existing AWS resources that might be
configured for github-events monitoring using available credentials.
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AWSResourceDiscovery:
    """Discover existing AWS resources for github-events."""
    
    def __init__(self):
        self.regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1']
        self.discovered_resources = {
            'dynamodb_tables': [],
            's3_buckets': [],
            'lambda_functions': [],
            'ecs_clusters': [],
            'codebuild_projects': [],
            'cloudwatch_dashboards': []
        }
    
    async def check_aws_credentials(self) -> Dict[str, Any]:
        """Check available AWS credentials and access."""
        credentials_info = {
            'available': False,
            'source': None,
            'identity': None,
            'regions_accessible': []
        }
        
        # Check different credential sources
        credential_sources = [
            ('Environment Variables', self._check_env_credentials),
            ('AWS CLI Profile', self._check_cli_profile),
            ('IAM Role', self._check_iam_role),
            ('Instance Metadata', self._check_instance_metadata)
        ]
        
        for source_name, check_func in credential_sources:
            try:
                result = await check_func()
                if result['available']:
                    credentials_info.update(result)
                    credentials_info['source'] = source_name
                    logger.info(f"✅ AWS credentials found via {source_name}")
                    break
            except Exception as e:
                logger.debug(f"❌ {source_name} check failed: {e}")
        
        return credentials_info
    
    async def _check_env_credentials(self) -> Dict[str, Any]:
        """Check for environment variable credentials."""
        if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
            try:
                sts = boto3.client('sts')
                identity = sts.get_caller_identity()
                return {
                    'available': True,
                    'identity': identity,
                    'regions_accessible': await self._test_regions()
                }
            except Exception as e:
                logger.error(f"Environment credentials invalid: {e}")
        
        return {'available': False}
    
    async def _check_cli_profile(self) -> Dict[str, Any]:
        """Check for AWS CLI profile credentials."""
        try:
            # Try default profile
            session = boto3.Session()
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            return {
                'available': True,
                'identity': identity,
                'regions_accessible': await self._test_regions()
            }
        except Exception:
            pass
        
        return {'available': False}
    
    async def _check_iam_role(self) -> Dict[str, Any]:
        """Check for IAM role credentials."""
        try:
            # This would work if running on EC2 with IAM role
            session = boto3.Session()
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            
            if 'assumed-role' in identity.get('Arn', ''):
                return {
                    'available': True,
                    'identity': identity,
                    'regions_accessible': await self._test_regions()
                }
        except Exception:
            pass
        
        return {'available': False}
    
    async def _check_instance_metadata(self) -> Dict[str, Any]:
        """Check for EC2 instance metadata credentials."""
        try:
            # Try to access instance metadata
            result = subprocess.run([
                'curl', '-s', '--connect-timeout', '2',
                'http://169.254.169.254/latest/meta-data/iam/security-credentials/'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                # Instance metadata available
                session = boto3.Session()
                sts = session.client('sts')
                identity = sts.get_caller_identity()
                return {
                    'available': True,
                    'identity': identity,
                    'regions_accessible': await self._test_regions()
                }
        except Exception:
            pass
        
        return {'available': False}
    
    async def _test_regions(self) -> List[str]:
        """Test which AWS regions are accessible."""
        accessible_regions = []
        
        for region in self.regions:
            try:
                ec2 = boto3.client('ec2', region_name=region)
                ec2.describe_regions()
                accessible_regions.append(region)
            except Exception:
                continue
        
        return accessible_regions
    
    async def discover_dynamodb_tables(self) -> List[Dict[str, Any]]:
        """Discover DynamoDB tables related to github-events."""
        tables = []
        
        for region in self.regions:
            try:
                dynamodb = boto3.client('dynamodb', region_name=region)
                response = dynamodb.list_tables()
                
                # Filter for github-events related tables
                github_events_tables = [
                    table for table in response['TableNames']
                    if 'github-events' in table.lower() or 'github_events' in table.lower()
                ]
                
                for table_name in github_events_tables:
                    try:
                        table_info = dynamodb.describe_table(TableName=table_name)
                        tables.append({
                            'name': table_name,
                            'region': region,
                            'status': table_info['Table']['TableStatus'],
                            'item_count': table_info['Table'].get('ItemCount', 0),
                            'size_bytes': table_info['Table'].get('TableSizeBytes', 0),
                            'created': table_info['Table'].get('CreationDateTime', '').isoformat() if table_info['Table'].get('CreationDateTime') else None
                        })
                        logger.info(f"Found DynamoDB table: {table_name} in {region}")
                    except Exception as e:
                        logger.error(f"Error describing table {table_name}: {e}")
                
            except Exception as e:
                logger.debug(f"Cannot access DynamoDB in {region}: {e}")
        
        return tables
    
    async def discover_s3_buckets(self) -> List[Dict[str, Any]]:
        """Discover S3 buckets related to github-events."""
        buckets = []
        
        try:
            s3 = boto3.client('s3')
            response = s3.list_buckets()
            
            # Filter for github-events related buckets
            github_events_buckets = [
                bucket for bucket in response['Buckets']
                if 'github-events' in bucket['Name'].lower() or 'github_events' in bucket['Name'].lower()
            ]
            
            for bucket in github_events_buckets:
                try:
                    # Get bucket location
                    location = s3.get_bucket_location(Bucket=bucket['Name'])
                    region = location.get('LocationConstraint', 'us-east-1')
                    
                    # Get bucket size (approximate)
                    try:
                        cloudwatch = boto3.client('cloudwatch', region_name=region)
                        metrics = cloudwatch.get_metric_statistics(
                            Namespace='AWS/S3',
                            MetricName='BucketSizeBytes',
                            Dimensions=[
                                {'Name': 'BucketName', 'Value': bucket['Name']},
                                {'Name': 'StorageType', 'Value': 'StandardStorage'}
                            ],
                            StartTime=datetime.now(timezone.utc) - timedelta(days=2),
                            EndTime=datetime.now(timezone.utc),
                            Period=86400,
                            Statistics=['Average']
                        )
                        size_bytes = metrics['Datapoints'][-1]['Average'] if metrics['Datapoints'] else 0
                    except Exception:
                        size_bytes = 0
                    
                    buckets.append({
                        'name': bucket['Name'],
                        'region': region,
                        'created': bucket['CreationDate'].isoformat(),
                        'size_bytes': size_bytes
                    })
                    logger.info(f"Found S3 bucket: {bucket['Name']} in {region}")
                    
                except Exception as e:
                    logger.error(f"Error analyzing bucket {bucket['Name']}: {e}")
        
        except Exception as e:
            logger.debug(f"Cannot access S3: {e}")
        
        return buckets
    
    async def discover_lambda_functions(self) -> List[Dict[str, Any]]:
        """Discover Lambda functions related to github-events."""
        functions = []
        
        for region in self.regions:
            try:
                lambda_client = boto3.client('lambda', region_name=region)
                response = lambda_client.list_functions()
                
                # Filter for github-events related functions
                github_events_functions = [
                    func for func in response['Functions']
                    if 'github-events' in func['FunctionName'].lower() or 'github_events' in func['FunctionName'].lower()
                ]
                
                for func in github_events_functions:
                    functions.append({
                        'name': func['FunctionName'],
                        'region': region,
                        'runtime': func['Runtime'],
                        'last_modified': func['LastModified'],
                        'description': func.get('Description', ''),
                        'memory_size': func['MemorySize'],
                        'timeout': func['Timeout']
                    })
                    logger.info(f"Found Lambda function: {func['FunctionName']} in {region}")
                
            except Exception as e:
                logger.debug(f"Cannot access Lambda in {region}: {e}")
        
        return functions
    
    async def discover_all_resources(self) -> Dict[str, Any]:
        """Discover all AWS resources related to github-events."""
        logger.info("🔍 Starting AWS resource discovery for github-events...")
        
        # Check credentials first
        credentials = await self.check_aws_credentials()
        
        if not credentials['available']:
            return {
                'credentials_available': False,
                'message': 'No AWS credentials found. Please configure AWS access.',
                'setup_instructions': {
                    'option_1': 'Set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY',
                    'option_2': 'Configure AWS CLI: aws configure',
                    'option_3': 'Use IAM role if running on EC2',
                    'option_4': 'Use GitHub Actions secrets if in CI/CD'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        logger.info(f"✅ AWS credentials available via {credentials['source']}")
        logger.info(f"Identity: {credentials['identity'].get('Arn', 'Unknown')}")
        
        discovery_results = {
            'credentials': credentials,
            'discovery_timestamp': datetime.now(timezone.utc).isoformat(),
            'resources_found': {}
        }
        
        # Discover resources in parallel
        discovery_tasks = [
            ('dynamodb_tables', self.discover_dynamodb_tables()),
            ('s3_buckets', self.discover_s3_buckets()),
            ('lambda_functions', self.discover_lambda_functions())
        ]
        
        for resource_type, task in discovery_tasks:
            try:
                resources = await task
                discovery_results['resources_found'][resource_type] = resources
                logger.info(f"Found {len(resources)} {resource_type}")
            except Exception as e:
                logger.error(f"Failed to discover {resource_type}: {e}")
                discovery_results['resources_found'][resource_type] = []
        
        return discovery_results
    
    def generate_aws_setup_script(self, discovered_resources: Dict[str, Any]) -> str:
        """Generate setup script based on discovered resources."""
        script = """#!/bin/bash

# AWS Setup Script for GitHub Events Monitor
# Generated based on resource discovery

echo "🔧 Setting up AWS resources for GitHub Events Monitor"
echo "=================================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured"
    echo "Please run: aws configure"
    echo "Or set environment variables:"
    echo "  export AWS_ACCESS_KEY_ID=your_access_key"
    echo "  export AWS_SECRET_ACCESS_KEY=your_secret_key"
    echo "  export AWS_DEFAULT_REGION=us-east-1"
    exit 1
fi

echo "✅ AWS credentials configured"

"""
        
        # Add resource-specific setup based on discoveries
        resources = discovered_resources.get('resources_found', {})
        
        if resources.get('dynamodb_tables'):
            script += """
# DynamoDB tables found - configure for github-events
echo "📊 Configuring existing DynamoDB tables..."
export DATABASE_PROVIDER=dynamodb
export DYNAMODB_TABLE_PREFIX=github-events-

"""
        else:
            script += """
# No DynamoDB tables found - create new ones
echo "📊 Creating DynamoDB tables for github-events..."
python scripts/setup_dynamodb.py create

"""
        
        if resources.get('s3_buckets'):
            script += """
# S3 buckets found - configure for artifacts
echo "📁 Using existing S3 buckets for artifacts..."

"""
        else:
            script += """
# Create S3 bucket for github-events artifacts
echo "📁 Creating S3 bucket for github-events..."
aws s3 mb s3://github-events-artifacts-$(date +%s) --region us-east-1

"""
        
        script += """
echo "✅ AWS setup completed for GitHub Events Monitor"
echo "🌐 You can now start the API with DynamoDB backend:"
echo "  export DATABASE_PROVIDER=dynamodb"
echo "  python -m src.github_events_monitor.api"
"""
        
        return script


async def main():
    """Main discovery function."""
    print("🔍 AWS Resource Discovery for GitHub Events Monitor")
    print("=" * 55)
    
    discovery = AWSResourceDiscovery()
    
    # Discover resources
    results = await discovery.discover_all_resources()
    
    # Print results
    print("\n📋 Discovery Results:")
    print("=" * 30)
    
    if not results.get('credentials_available', True):
        print("❌ No AWS credentials available")
        print("\n🔧 Setup Instructions:")
        setup_instructions = results.get('setup_instructions', {})
        for option, instruction in setup_instructions.items():
            print(f"  {option}: {instruction}")
        return
    
    # Print credential info
    creds = results.get('credentials', {})
    print(f"✅ AWS Access Available")
    print(f"   Source: {creds.get('source', 'Unknown')}")
    print(f"   Identity: {creds.get('identity', {}).get('Arn', 'Unknown')}")
    print(f"   Regions: {', '.join(creds.get('regions_accessible', []))}")
    
    # Print discovered resources
    resources = results.get('resources_found', {})
    
    print(f"\n📊 DynamoDB Tables: {len(resources.get('dynamodb_tables', []))}")
    for table in resources.get('dynamodb_tables', []):
        print(f"   - {table['name']} ({table['region']}) - {table['status']}")
    
    print(f"\n📁 S3 Buckets: {len(resources.get('s3_buckets', []))}")
    for bucket in resources.get('s3_buckets', []):
        print(f"   - {bucket['name']} ({bucket['region']}) - {bucket.get('size_bytes', 0)} bytes")
    
    print(f"\n⚡ Lambda Functions: {len(resources.get('lambda_functions', []))}")
    for func in resources.get('lambda_functions', []):
        print(f"   - {func['name']} ({func['region']}) - {func['runtime']}")
    
    # Generate setup script
    if results.get('credentials_available', True):
        setup_script = discovery.generate_aws_setup_script(results)
        
        with open('aws_github_events_setup.sh', 'w') as f:
            f.write(setup_script)
        
        print(f"\n🔧 Generated setup script: aws_github_events_setup.sh")
        print("   Run this script to configure AWS resources for github-events")
    
    # Save discovery results
    with open('aws_resource_discovery.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Discovery results saved to: aws_resource_discovery.json")
    
    # Provide next steps
    print(f"\n🚀 Next Steps:")
    if resources.get('dynamodb_tables'):
        print("   1. ✅ DynamoDB tables found - configure DATABASE_PROVIDER=dynamodb")
    else:
        print("   1. 📊 Create DynamoDB tables: python scripts/setup_dynamodb.py create")
    
    if resources.get('s3_buckets'):
        print("   2. ✅ S3 buckets found - configure artifact storage")
    else:
        print("   2. 📁 Create S3 bucket for artifacts")
    
    print("   3. 🚀 Start github-events with AWS backend:")
    print("      export DATABASE_PROVIDER=dynamodb")
    print("      python -m src.github_events_monitor.api")


if __name__ == "__main__":
    asyncio.run(main())