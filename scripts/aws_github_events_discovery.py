#!/usr/bin/env python3
"""
AWS GitHub Events Discovery and Setup

Comprehensive script to discover existing AWS resources for github-events
and provide setup guidance based on available access.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GitHubEventsAWSDiscovery:
    """Discover and configure AWS services for GitHub Events Monitor."""
    
    def __init__(self):
        self.regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1']
        self.github_events_patterns = [
            'github-events',
            'github_events', 
            'githubevents',
            'sparesparrow-github-events',
            'openssl-refactor',
            'agents-github-events'
        ]
    
    async def comprehensive_discovery(self) -> Dict[str, Any]:
        """Perform comprehensive AWS resource discovery."""
        discovery_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'aws_access': await self._check_aws_access(),
            'existing_resources': {},
            'recommended_setup': {},
            'configuration_guide': {}
        }
        
        if discovery_results['aws_access']['available']:
            logger.info("✅ AWS access available - performing resource discovery")
            discovery_results['existing_resources'] = await self._discover_existing_resources()
            discovery_results['recommended_setup'] = await self._generate_recommended_setup()
        else:
            logger.warning("❌ No AWS access - providing configuration guidance")
            discovery_results['configuration_guide'] = await self._generate_configuration_guide()
        
        return discovery_results
    
    async def _check_aws_access(self) -> Dict[str, Any]:
        """Check for AWS access through various methods."""
        access_methods = [
            ('AWS CLI Profile', self._test_aws_cli),
            ('Environment Variables', self._test_env_vars),
            ('IAM Role/Instance Metadata', self._test_iam_role),
            ('GitHub Actions Context', self._test_github_actions)
        ]
        
        for method_name, test_func in access_methods:
            try:
                if await test_func():
                    identity = await self._get_aws_identity()
                    return {
                        'available': True,
                        'method': method_name,
                        'identity': identity,
                        'regions': await self._test_accessible_regions()
                    }
            except Exception as e:
                logger.debug(f"{method_name} test failed: {e}")
        
        return {
            'available': False,
            'method': None,
            'setup_required': True
        }
    
    async def _test_aws_cli(self) -> bool:
        """Test AWS CLI access."""
        try:
            result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    async def _test_env_vars(self) -> bool:
        """Test environment variable credentials."""
        return bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))
    
    async def _test_iam_role(self) -> bool:
        """Test IAM role access."""
        try:
            result = subprocess.run([
                'curl', '-s', '--connect-timeout', '2',
                'http://169.254.169.254/latest/meta-data/iam/security-credentials/'
            ], capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False
    
    async def _test_github_actions(self) -> bool:
        """Test GitHub Actions context."""
        return bool(os.getenv('GITHUB_ACTIONS') and 
                   (os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('GITHUB_TOKEN')))
    
    async def _get_aws_identity(self) -> Optional[Dict[str, Any]]:
        """Get AWS caller identity."""
        try:
            result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            logger.debug(f"Failed to get AWS identity: {e}")
        
        return None
    
    async def _test_accessible_regions(self) -> List[str]:
        """Test which regions are accessible."""
        accessible = []
        
        for region in self.regions:
            try:
                result = subprocess.run([
                    'aws', 'ec2', 'describe-regions', '--region', region
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    accessible.append(region)
            except Exception:
                continue
        
        return accessible
    
    async def _discover_existing_resources(self) -> Dict[str, Any]:
        """Discover existing AWS resources for github-events."""
        resources = {
            'dynamodb_tables': await self._find_dynamodb_tables(),
            's3_buckets': await self._find_s3_buckets(),
            'lambda_functions': await self._find_lambda_functions(),
            'ecs_clusters': await self._find_ecs_clusters(),
            'codebuild_projects': await self._find_codebuild_projects(),
            'cloudwatch_dashboards': await self._find_cloudwatch_dashboards()
        }
        
        return resources
    
    async def _find_dynamodb_tables(self) -> List[Dict[str, Any]]:
        """Find DynamoDB tables related to github-events."""
        tables = []
        
        for region in self.regions:
            try:
                result = subprocess.run([
                    'aws', 'dynamodb', 'list-tables', '--region', region
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    table_data = json.loads(result.stdout)
                    
                    for table_name in table_data['TableNames']:
                        if any(pattern in table_name.lower() for pattern in self.github_events_patterns):
                            # Get table details
                            detail_result = subprocess.run([
                                'aws', 'dynamodb', 'describe-table',
                                '--table-name', table_name,
                                '--region', region
                            ], capture_output=True, text=True, timeout=30)
                            
                            if detail_result.returncode == 0:
                                table_detail = json.loads(detail_result.stdout)
                                tables.append({
                                    'name': table_name,
                                    'region': region,
                                    'status': table_detail['Table']['TableStatus'],
                                    'item_count': table_detail['Table'].get('ItemCount', 0),
                                    'size_bytes': table_detail['Table'].get('TableSizeBytes', 0)
                                })
                                logger.info(f"Found DynamoDB table: {table_name} in {region}")
            
            except Exception as e:
                logger.debug(f"Error checking DynamoDB in {region}: {e}")
        
        return tables
    
    async def _find_s3_buckets(self) -> List[Dict[str, Any]]:
        """Find S3 buckets related to github-events."""
        buckets = []
        
        try:
            result = subprocess.run([
                'aws', 's3api', 'list-buckets'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                bucket_data = json.loads(result.stdout)
                
                for bucket in bucket_data['Buckets']:
                    if any(pattern in bucket['Name'].lower() for pattern in self.github_events_patterns):
                        # Get bucket location
                        location_result = subprocess.run([
                            'aws', 's3api', 'get-bucket-location',
                            '--bucket', bucket['Name']
                        ], capture_output=True, text=True, timeout=15)
                        
                        region = 'us-east-1'  # Default
                        if location_result.returncode == 0:
                            location_data = json.loads(location_result.stdout)
                            region = location_data.get('LocationConstraint', 'us-east-1')
                        
                        buckets.append({
                            'name': bucket['Name'],
                            'region': region,
                            'created': bucket['CreationDate']
                        })
                        logger.info(f"Found S3 bucket: {bucket['Name']}")
        
        except Exception as e:
            logger.debug(f"Error checking S3: {e}")
        
        return buckets
    
    async def _find_lambda_functions(self) -> List[Dict[str, Any]]:
        """Find Lambda functions related to github-events."""
        functions = []
        
        for region in self.regions:
            try:
                result = subprocess.run([
                    'aws', 'lambda', 'list-functions', '--region', region
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    func_data = json.loads(result.stdout)
                    
                    for func in func_data['Functions']:
                        if any(pattern in func['FunctionName'].lower() for pattern in self.github_events_patterns):
                            functions.append({
                                'name': func['FunctionName'],
                                'region': region,
                                'runtime': func['Runtime'],
                                'description': func.get('Description', ''),
                                'last_modified': func['LastModified']
                            })
                            logger.info(f"Found Lambda function: {func['FunctionName']} in {region}")
            
            except Exception as e:
                logger.debug(f"Error checking Lambda in {region}: {e}")
        
        return functions
    
    async def _find_ecs_clusters(self) -> List[Dict[str, Any]]:
        """Find ECS clusters related to github-events."""
        clusters = []
        
        for region in self.regions:
            try:
                result = subprocess.run([
                    'aws', 'ecs', 'list-clusters', '--region', region
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    cluster_data = json.loads(result.stdout)
                    
                    for cluster_arn in cluster_data['clusterArns']:
                        cluster_name = cluster_arn.split('/')[-1]
                        if any(pattern in cluster_name.lower() for pattern in self.github_events_patterns):
                            clusters.append({
                                'name': cluster_name,
                                'arn': cluster_arn,
                                'region': region
                            })
                            logger.info(f"Found ECS cluster: {cluster_name} in {region}")
            
            except Exception as e:
                logger.debug(f"Error checking ECS in {region}: {e}")
        
        return clusters
    
    async def _find_codebuild_projects(self) -> List[Dict[str, Any]]:
        """Find CodeBuild projects related to github-events."""
        projects = []
        
        for region in self.regions:
            try:
                result = subprocess.run([
                    'aws', 'codebuild', 'list-projects', '--region', region
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    project_data = json.loads(result.stdout)
                    
                    for project_name in project_data['projects']:
                        if any(pattern in project_name.lower() for pattern in self.github_events_patterns):
                            projects.append({
                                'name': project_name,
                                'region': region
                            })
                            logger.info(f"Found CodeBuild project: {project_name} in {region}")
            
            except Exception as e:
                logger.debug(f"Error checking CodeBuild in {region}: {e}")
        
        return projects
    
    async def _find_cloudwatch_dashboards(self) -> List[Dict[str, Any]]:
        """Find CloudWatch dashboards related to github-events."""
        dashboards = []
        
        for region in self.regions:
            try:
                result = subprocess.run([
                    'aws', 'cloudwatch', 'list-dashboards', '--region', region
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    dashboard_data = json.loads(result.stdout)
                    
                    for dashboard in dashboard_data['DashboardEntries']:
                        if any(pattern in dashboard['DashboardName'].lower() for pattern in self.github_events_patterns):
                            dashboards.append({
                                'name': dashboard['DashboardName'],
                                'region': region,
                                'last_modified': dashboard['LastModified']
                            })
                            logger.info(f"Found CloudWatch dashboard: {dashboard['DashboardName']} in {region}")
            
            except Exception as e:
                logger.debug(f"Error checking CloudWatch in {region}: {e}")
        
        return dashboards
    
    async def _generate_recommended_setup(self) -> Dict[str, Any]:
        """Generate recommended AWS setup based on github-events requirements."""
        return {
            'dynamodb_tables': [
                {
                    'name': 'github-events-events',
                    'purpose': 'Store GitHub events data',
                    'key_schema': 'id (HASH)',
                    'gsi': ['repo-created-index', 'type-created-index']
                },
                {
                    'name': 'github-events-commits',
                    'purpose': 'Store commit details and analysis',
                    'key_schema': 'sha (HASH)',
                    'gsi': ['repo-date-index']
                },
                {
                    'name': 'github-events-metrics',
                    'purpose': 'Store repository health and metrics',
                    'key_schema': 'repo_name (HASH)'
                }
            ],
            's3_buckets': [
                {
                    'name': 'github-events-artifacts',
                    'purpose': 'Store dashboard artifacts and reports',
                    'configuration': 'Static website hosting enabled'
                },
                {
                    'name': 'github-events-agent-coordination',
                    'purpose': 'Store agent coordination data and logs',
                    'configuration': 'Versioning enabled'
                }
            ],
            'lambda_functions': [
                {
                    'name': 'github-events-collector',
                    'purpose': 'Serverless event collection',
                    'runtime': 'python3.11',
                    'memory': '512MB',
                    'timeout': '5 minutes'
                },
                {
                    'name': 'github-events-analyzer',
                    'purpose': 'Repository analysis and health scoring',
                    'runtime': 'python3.11',
                    'memory': '1024MB',
                    'timeout': '10 minutes'
                }
            ],
            'iam_roles': [
                {
                    'name': 'GitHubEventsLambdaRole',
                    'purpose': 'Lambda execution role',
                    'permissions': ['DynamoDB access', 'CloudWatch logs', 'S3 access']
                },
                {
                    'name': 'GitHubEventsECSRole',
                    'purpose': 'ECS task execution role',
                    'permissions': ['DynamoDB access', 'S3 access', 'CloudWatch logs']
                }
            ]
        }
    
    async def _generate_configuration_guide(self) -> Dict[str, Any]:
        """Generate configuration guide when no AWS access is available."""
        return {
            'credential_setup': {
                'development': {
                    'method': 'Environment Variables',
                    'steps': [
                        'Get AWS credentials from AWS Console',
                        'export AWS_ACCESS_KEY_ID=your_access_key',
                        'export AWS_SECRET_ACCESS_KEY=your_secret_key',
                        'export AWS_DEFAULT_REGION=us-east-1',
                        'aws sts get-caller-identity  # Test access'
                    ]
                },
                'production': {
                    'method': 'IAM Roles',
                    'steps': [
                        'Create IAM role with required permissions',
                        'Attach role to EC2 instance or ECS task',
                        'No credential configuration needed',
                        'Automatic credential rotation'
                    ]
                },
                'cicd': {
                    'method': 'GitHub Actions Secrets',
                    'steps': [
                        'Go to GitHub repository Settings > Secrets',
                        'Add AWS_ACCESS_KEY_ID secret',
                        'Add AWS_SECRET_ACCESS_KEY secret',
                        'Add AWS_DEFAULT_REGION secret',
                        'Use in workflows with ${{ secrets.AWS_ACCESS_KEY_ID }}'
                    ]
                }
            },
            'required_permissions': [
                'dynamodb:CreateTable',
                'dynamodb:DescribeTable',
                'dynamodb:PutItem',
                'dynamodb:GetItem',
                'dynamodb:Query',
                'dynamodb:Scan',
                's3:CreateBucket',
                's3:PutObject',
                's3:GetObject',
                'lambda:CreateFunction',
                'lambda:InvokeFunction',
                'cloudwatch:PutDashboard',
                'cloudwatch:PutMetricData'
            ],
            'setup_commands': [
                'python3 scripts/setup_dynamodb.py create',
                'export DATABASE_PROVIDER=dynamodb',
                'python -m src.github_events_monitor.api'
            ]
        }
    
    def generate_infrastructure_as_code(self, resources: Dict[str, Any]) -> str:
        """Generate CloudFormation template for github-events infrastructure."""
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "GitHub Events Monitor Infrastructure",
            "Parameters": {
                "TablePrefix": {
                    "Type": "String",
                    "Default": "github-events-",
                    "Description": "Prefix for DynamoDB table names"
                }
            },
            "Resources": {
                # DynamoDB Tables
                "EventsTable": {
                    "Type": "AWS::DynamoDB::Table",
                    "Properties": {
                        "TableName": {"Fn::Sub": "${TablePrefix}events"},
                        "BillingMode": "PAY_PER_REQUEST",
                        "AttributeDefinitions": [
                            {"AttributeName": "id", "AttributeType": "S"},
                            {"AttributeName": "repo_name", "AttributeType": "S"},
                            {"AttributeName": "event_type", "AttributeType": "S"},
                            {"AttributeName": "created_at", "AttributeType": "S"}
                        ],
                        "KeySchema": [
                            {"AttributeName": "id", "KeyType": "HASH"}
                        ],
                        "GlobalSecondaryIndexes": [
                            {
                                "IndexName": "repo-created-index",
                                "KeySchema": [
                                    {"AttributeName": "repo_name", "KeyType": "HASH"},
                                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                                ],
                                "Projection": {"ProjectionType": "ALL"}
                            }
                        ]
                    }
                },
                
                # S3 Bucket
                "ArtifactsBucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": {"Fn::Sub": "${TablePrefix}artifacts"},
                        "WebsiteConfiguration": {
                            "IndexDocument": "index.html",
                            "ErrorDocument": "error.html"
                        },
                        "VersioningConfiguration": {
                            "Status": "Enabled"
                        }
                    }
                },
                
                # IAM Role for Lambda
                "LambdaExecutionRole": {
                    "Type": "AWS::IAM::Role",
                    "Properties": {
                        "RoleName": {"Fn::Sub": "${TablePrefix}lambda-role"},
                        "AssumeRolePolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"Service": "lambda.amazonaws.com"},
                                    "Action": "sts:AssumeRole"
                                }
                            ]
                        },
                        "ManagedPolicyArns": [
                            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                        ],
                        "Policies": [
                            {
                                "PolicyName": "GitHubEventsAccess",
                                "PolicyDocument": {
                                    "Version": "2012-10-17",
                                    "Statement": [
                                        {
                                            "Effect": "Allow",
                                            "Action": [
                                                "dynamodb:PutItem",
                                                "dynamodb:GetItem",
                                                "dynamodb:Query",
                                                "dynamodb:Scan"
                                            ],
                                            "Resource": {"Fn::Sub": "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${TablePrefix}*"}
                                        },
                                        {
                                            "Effect": "Allow",
                                            "Action": [
                                                "s3:PutObject",
                                                "s3:GetObject"
                                            ],
                                            "Resource": {"Fn::Sub": "${ArtifactsBucket}/*"}
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            },
            "Outputs": {
                "EventsTableName": {
                    "Description": "DynamoDB table for events",
                    "Value": {"Ref": "EventsTable"}
                },
                "ArtifactsBucketName": {
                    "Description": "S3 bucket for artifacts",
                    "Value": {"Ref": "ArtifactsBucket"}
                },
                "WebsiteURL": {
                    "Description": "Website URL",
                    "Value": {"Fn::GetAtt": ["ArtifactsBucket", "WebsiteURL"]}
                }
            }
        }
        
        return json.dumps(template, indent=2)


async def main():
    """Main discovery and setup function."""
    print("🔍 AWS GitHub Events Discovery and Setup")
    print("=" * 45)
    
    discovery = GitHubEventsAWSDiscovery()
    
    # Perform comprehensive discovery
    results = await discovery.comprehensive_discovery()
    
    # Display results
    print(f"\n📋 Discovery Results:")
    print(f"   Timestamp: {results['timestamp']}")
    
    aws_access = results['aws_access']
    if aws_access['available']:
        print(f"✅ AWS Access: Available via {aws_access['method']}")
        if aws_access.get('identity'):
            print(f"   Identity: {aws_access['identity'].get('Arn', 'Unknown')}")
        print(f"   Regions: {', '.join(aws_access.get('regions', []))}")
        
        # Show existing resources
        existing = results.get('existing_resources', {})
        total_resources = sum(len(resources) for resources in existing.values())
        
        print(f"\n📊 Existing Resources Found: {total_resources}")
        for resource_type, resources in existing.items():
            if resources:
                print(f"   {resource_type}: {len(resources)}")
                for resource in resources[:3]:  # Show first 3
                    print(f"     - {resource.get('name', 'Unknown')} ({resource.get('region', 'Unknown region')})")
        
        # Show recommended setup
        if total_resources == 0:
            recommended = results.get('recommended_setup', {})
            print(f"\n🔧 Recommended Setup:")
            for service_type, configs in recommended.items():
                print(f"   {service_type}: {len(configs)} items")
    else:
        print(f"❌ AWS Access: Not available")
        print(f"   Configuration needed: {aws_access.get('setup_required', True)}")
        
        # Show configuration guide
        config_guide = results.get('configuration_guide', {})
        if config_guide:
            print(f"\n🔧 Configuration Options:")
            for method, details in config_guide.get('credential_setup', {}).items():
                print(f"   {method.title()}: {details['method']}")
    
    # Generate CloudFormation template
    cf_template = discovery.generate_infrastructure_as_code(results)
    with open('github-events-infrastructure.yaml', 'w') as f:
        f.write(cf_template)
    
    print(f"\n📄 Files Generated:")
    print(f"   - aws_resource_discovery.json (discovery results)")
    print(f"   - github-events-infrastructure.yaml (CloudFormation template)")
    print(f"   - aws_configuration_guide.md (setup instructions)")
    
    # Save discovery results
    with open('aws_resource_discovery.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n🚀 Next Steps:")
    if aws_access['available']:
        print("   1. ✅ AWS access configured")
        print("   2. 📊 Deploy infrastructure: aws cloudformation deploy --template-file github-events-infrastructure.yaml --stack-name github-events")
        print("   3. 🔧 Configure github-events: export DATABASE_PROVIDER=dynamodb")
        print("   4. 🚀 Start monitoring: python -m src.github_events_monitor.api")
    else:
        print("   1. 🔑 Configure AWS credentials (see aws_configuration_guide.md)")
        print("   2. 🔍 Re-run discovery: python3 scripts/aws_github_events_discovery.py")
        print("   3. 📊 Deploy infrastructure using CloudFormation template")
        print("   4. 🚀 Start github-events with AWS backend")
    
    print(f"\n🎯 For OpenSSL refactoring monitoring:")
    print("   ./start_openssl_refactor_monitoring.sh")
    
    print(f"\n🤖 For agent ecosystem with AWS:")
    print("   export DATABASE_PROVIDER=dynamodb")
    print("   ./start_agent_ecosystem.sh")


if __name__ == "__main__":
    asyncio.run(main())