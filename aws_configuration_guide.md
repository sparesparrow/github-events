
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
