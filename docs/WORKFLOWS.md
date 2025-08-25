# GitHub Actions Workflows

This repository includes four comprehensive GitHub Actions workflows:

## 1. CI/CD Pipeline (`ci-cd.yml`)
- **Triggers**: Push to main/develop, PRs, daily schedule
- **Jobs**: Test & build, example usage, visualizations, deployment
- **Features**: 
  - Comprehensive testing with coverage
  - Docker build and test
  - Live API examples with real data
  - Automatic visualization generation
  - GitHub Pages deployment

## 2. API Monitoring (`api-monitoring.yml`)
- **Triggers**: Hourly schedule, manual dispatch  
- **Jobs**: API health monitoring and metrics collection
- **Features**:
  - Endpoint availability testing
  - Response time monitoring
  - Success rate tracking
  - Automated alerts on failures

## 3. Performance Testing (`performance-testing.yml`)
- **Triggers**: Manual dispatch, releases
- **Jobs**: Load testing with Locust
- **Features**:
  - Configurable concurrent users
  - Response time benchmarking
  - Performance regression detection
  - Load test reports

## 4. Documentation (`documentation.yml`)
- **Triggers**: Push to main, manual dispatch
- **Jobs**: API docs generation and deployment
- **Features**:
  - OpenAPI spec generation
  - Usage examples creation
  - GitHub Pages deployment
  - Interactive documentation

## Setup Instructions

1. Copy workflow files to `.github/workflows/`
2. Ensure `GITHUB_TOKEN` secret is available (automatic)
3. Enable GitHub Pages in repository settings
4. Customize parameters as needed

## Usage

- Workflows run automatically on triggers
- Manual triggers available via GitHub Actions tab
- Results available as artifacts and GitHub Pages
- Monitoring data helps track API health over time

## Visualization Outputs

- API response dashboards
- Performance trend charts  
- System health metrics
- Interactive documentation
- Load test reports

All visualizations are automatically deployed to GitHub Pages for easy access.
