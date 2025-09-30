#!/usr/bin/env python3
"""
AWS Setup and Configuration for GitHub Events Monitor

This script helps set up AWS services for github-events monitoring,
including credential configuration and resource discovery.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AWSGitHubEventsSetup:
    """Setup AWS services for GitHub Events Monitor."""
    
    def __init__(self):
        self.aws_configured = False
        self.available_regions = ['us-east-1', 'us-west-2', 'eu-west-1']
        
    async def check_aws_access(self) -> Dict[str, Any]:
        """Check AWS access and configuration options."""
        access_methods = {
            'environment_variables': self._check_env_vars(),
            'aws_cli_profile': self._check_aws_cli(),
            'iam_role': self._check_iam_role(),
            'github_actions': self._check_github_actions(),
            'manual_configuration': True  # Always available as fallback
        }
        
        # Find the first available method
        for method, available in access_methods.items():
            if available and method != 'manual_configuration':
                logger.info(f"✅ AWS access available via {method}")
                return {
                    'access_available': True,
                    'method': method,
                    'configuration_needed': False
                }
        
        logger.warning("❌ No AWS credentials found")
        return {
            'access_available': False,
            'method': 'manual_configuration',
            'configuration_needed': True,
            'setup_options': {
                'option_1': {
                    'name': 'Environment Variables',
                    'commands': [
                        'export AWS_ACCESS_KEY_ID=your_access_key',
                        'export AWS_SECRET_ACCESS_KEY=your_secret_key',
                        'export AWS_DEFAULT_REGION=us-east-1'
                    ]
                },
                'option_2': {
                    'name': 'AWS CLI Configuration',
                    'commands': [
                        'aws configure',
                        '# Enter your AWS Access Key ID',
                        '# Enter your AWS Secret Access Key',
                        '# Enter default region (us-east-1)',
                        '# Enter output format (json)'
                    ]
                },
                'option_3': {
                    'name': 'GitHub Actions Secrets',
                    'commands': [
                        '# In GitHub repository settings, add secrets:',
                        '# AWS_ACCESS_KEY_ID',
                        '# AWS_SECRET_ACCESS_KEY',
                        '# AWS_DEFAULT_REGION'
                    ]
                }
            }
        }
    
    def _check_env_vars(self) -> bool:
        """Check for AWS environment variables."""
        return bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))
    
    def _check_aws_cli(self) -> bool:
        """Check for AWS CLI configuration."""
        try:
            result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_iam_role(self) -> bool:
        """Check for IAM role access."""
        try:
            # Check for instance metadata
            result = subprocess.run([
                'curl', '-s', '--connect-timeout', '2',
                'http://169.254.169.254/latest/meta-data/iam/security-credentials/'
            ], capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False
    
    def _check_github_actions(self) -> bool:
        """Check for GitHub Actions environment."""
        return bool(os.getenv('GITHUB_ACTIONS') and 
                   (os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('GITHUB_TOKEN')))
    
    async def create_aws_resources_for_github_events(self, region: str = 'us-east-1') -> Dict[str, Any]:
        """Create AWS resources for github-events monitoring."""
        logger.info(f"Creating AWS resources for github-events in {region}")
        
        resources_created = {
            'region': region,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resources': {}
        }
        
        try:
            import boto3
            
            # Create DynamoDB tables
            logger.info("📊 Creating DynamoDB tables...")
            dynamodb_result = await self._create_dynamodb_tables(region)
            resources_created['resources']['dynamodb'] = dynamodb_result
            
            # Create S3 bucket
            logger.info("📁 Creating S3 bucket...")
            s3_result = await self._create_s3_bucket(region)
            resources_created['resources']['s3'] = s3_result
            
            # Create Lambda functions
            logger.info("⚡ Creating Lambda functions...")
            lambda_result = await self._create_lambda_functions(region)
            resources_created['resources']['lambda'] = lambda_result
            
            # Create CloudWatch dashboard
            logger.info("📈 Creating CloudWatch dashboard...")
            cloudwatch_result = await self._create_cloudwatch_dashboard(region)
            resources_created['resources']['cloudwatch'] = cloudwatch_result
            
            resources_created['status'] = 'success'
            
        except ImportError:
            resources_created['status'] = 'failed'
            resources_created['error'] = 'boto3 not available - install with: pip install boto3'
        except Exception as e:
            resources_created['status'] = 'failed'
            resources_created['error'] = str(e)
            logger.error(f"Failed to create AWS resources: {e}")
        
        return resources_created
    
    async def _create_dynamodb_tables(self, region: str) -> Dict[str, Any]:
        """Create DynamoDB tables for github-events."""
        try:
            # Use our existing setup script
            result = subprocess.run([
                'python3', 'scripts/setup_dynamodb.py', 'create'
            ], capture_output=True, text=True, timeout=60,
            env={**os.environ, 'AWS_REGION': region, 'DYNAMODB_TABLE_PREFIX': 'github-events-'})
            
            if result.returncode == 0:
                return {
                    'status': 'success',
                    'output': result.stdout,
                    'tables_created': 'github-events-*'
                }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr,
                    'output': result.stdout
                }
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    async def _create_s3_bucket(self, region: str) -> Dict[str, Any]:
        """Create S3 bucket for github-events artifacts."""
        bucket_name = f"github-events-artifacts-{datetime.now().strftime('%Y%m%d')}"
        
        try:
            result = subprocess.run([
                'aws', 's3', 'mb', f's3://{bucket_name}', '--region', region
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Configure bucket for static website hosting
                subprocess.run([
                    'aws', 's3', 'website', f's3://{bucket_name}',
                    '--index-document', 'index.html'
                ], capture_output=True, text=True, timeout=30)
                
                return {
                    'status': 'success',
                    'bucket_name': bucket_name,
                    'region': region,
                    'website_endpoint': f'http://{bucket_name}.s3-website-{region}.amazonaws.com'
                }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr
                }
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    async def _create_lambda_functions(self, region: str) -> Dict[str, Any]:
        """Create Lambda functions for github-events processing."""
        # For now, return placeholder - would need proper deployment package
        return {
            'status': 'planned',
            'functions': [
                'github-events-collector',
                'github-events-analyzer', 
                'github-events-reporter'
            ],
            'note': 'Lambda functions require deployment package creation'
        }
    
    async def _create_cloudwatch_dashboard(self, region: str) -> Dict[str, Any]:
        """Create CloudWatch dashboard for github-events monitoring."""
        dashboard_name = 'GitHub-Events-Monitor'
        
        try:
            dashboard_body = {
                "widgets": [
                    {
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                ["GitHub-Events", "EventsCollected"],
                                [".", "RepositoriesMonitored"],
                                [".", "HealthScore"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": region,
                            "title": "GitHub Events Monitoring"
                        }
                    }
                ]
            }
            
            result = subprocess.run([
                'aws', 'cloudwatch', 'put-dashboard',
                '--dashboard-name', dashboard_name,
                '--dashboard-body', json.dumps(dashboard_body),
                '--region', region
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return {
                    'status': 'success',
                    'dashboard_name': dashboard_name,
                    'dashboard_url': f'https://console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={dashboard_name}'
                }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr
                }
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def generate_configuration_guide(self) -> str:
        """Generate configuration guide for AWS setup."""
        return """
# AWS Configuration Guide for GitHub Events Monitor

## Option 1: Environment Variables (Recommended for Development)
```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here  
export AWS_DEFAULT_REGION=us-east-1

# Test configuration
aws sts get-caller-identity
```

## Option 2: AWS CLI Configuration
```bash
aws configure
# AWS Access Key ID: your_access_key_here
# AWS Secret Access Key: your_secret_key_here
# Default region name: us-east-1
# Default output format: json
```

## Option 3: GitHub Actions Secrets (for CI/CD)
Add these secrets to your GitHub repository:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_DEFAULT_REGION

## Option 4: IAM Role (for EC2/ECS)
Attach IAM role with these permissions:
- DynamoDB: CreateTable, PutItem, GetItem, Query, Scan
- S3: CreateBucket, PutObject, GetObject
- Lambda: CreateFunction, InvokeFunction
- CloudWatch: PutDashboard, PutMetricData

## After Configuration:
```bash
# Verify access
python3 scripts/discover_aws_resources.py

# Create resources
python3 scripts/setup_dynamodb.py create

# Start github-events with AWS backend
export DATABASE_PROVIDER=dynamodb
python -m src.github_events_monitor.api
```
"""


async def main():
    """Main setup function."""
    print("🔧 AWS Setup for GitHub Events Monitor")
    print("=" * 40)
    
    setup = AWSGitHubEventsSetup()
    
    # Check AWS access
    access_info = await setup.check_aws_access()
    
    if access_info['access_available']:
        print("✅ AWS access is available!")
        print(f"   Method: {access_info['method']}")
        
        # Ask if user wants to create resources
        try:
            response = input("\n🚀 Create AWS resources for github-events? (y/N): ")
            if response.lower() in ['y', 'yes']:
                region = input("Enter AWS region (default: us-east-1): ") or 'us-east-1'
                
                print(f"\n📦 Creating AWS resources in {region}...")
                resources = await setup.create_aws_resources_for_github_events(region)
                
                print(f"\n📋 Resource Creation Results:")
                print(json.dumps(resources, indent=2, default=str))
                
                # Save results
                with open('aws_github_events_setup.json', 'w') as f:
                    json.dump(resources, f, indent=2, default=str)
                
                print(f"\n✅ Setup results saved to: aws_github_events_setup.json")
            else:
                print("⏭️ Skipping resource creation")
                
        except KeyboardInterrupt:
            print("\n⏹️ Setup cancelled by user")
            return
    else:
        print("❌ No AWS credentials available")
        print("\n🔧 Configuration needed:")
        
        setup_options = access_info.get('setup_options', {})
        for option_key, option_info in setup_options.items():
            print(f"\n{option_info['name']}:")
            for cmd in option_info['commands']:
                print(f"   {cmd}")
        
        # Generate configuration guide
        guide = setup.generate_configuration_guide()
        
        with open('aws_configuration_guide.md', 'w') as f:
            f.write(guide)
        
        print(f"\n📄 Detailed configuration guide saved to: aws_configuration_guide.md")
    
    # Show current github-events configuration
    print(f"\n📊 Current GitHub Events Configuration:")
    print(f"   Database Provider: {os.getenv('DATABASE_PROVIDER', 'sqlite')}")
    print(f"   Database Path: {os.getenv('DATABASE_PATH', './github_events.db')}")
    print(f"   Target Repositories: {os.getenv('TARGET_REPOSITORIES', 'Not set')}")
    
    # Show next steps
    print(f"\n🚀 Next Steps:")
    if access_info['access_available']:
        print("   1. ✅ AWS access configured")
        print("   2. 📊 Create DynamoDB tables: python scripts/setup_dynamodb.py create")
        print("   3. 🚀 Start with DynamoDB: export DATABASE_PROVIDER=dynamodb")
        print("   4. 🌐 Launch API: python -m src.github_events_monitor.api")
    else:
        print("   1. 🔑 Configure AWS credentials (see aws_configuration_guide.md)")
        print("   2. 🔍 Run discovery: python scripts/discover_aws_resources.py")
        print("   3. 📊 Create resources: python scripts/setup_dynamodb.py create")
        print("   4. 🚀 Start monitoring with AWS backend")
    
    print(f"\n🎯 For OpenSSL refactoring monitoring:")
    print("   ./start_openssl_refactor_monitoring.sh")
    
    print(f"\n🤖 For agent ecosystem:")
    print("   ./start_agent_ecosystem.sh")


if __name__ == "__main__":
    asyncio.run(main())