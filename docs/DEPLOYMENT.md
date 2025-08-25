# Deployment Guide

## Overview

This guide covers all deployment options for the GitHub Events Monitor, from local development to production environments.

## Quick Start Options

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/sparesparrow/github-events.git
cd github-events

# Create environment file
cp .env.template .env
# Edit .env and add your GITHUB_TOKEN

# Start with Docker Compose
docker-compose up -d

# Verify deployment
curl http://localhost:8000/health
```

### Option 2: Local Python

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN=your_github_token_here
export DATABASE_PATH=./github_events.db

# Run REST API server
python -m github_events_monitor.api

# In another terminal, run MCP server (optional)
python -m github_events_monitor.mcp_server
```

## Environment Configuration

### Required Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Recommended | None | GitHub Personal Access Token for higher rate limits |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./github_events.db` | Path to SQLite database file |
| `API_HOST` | `0.0.0.0` | API server bind address |
| `API_PORT` | `8000` | API server port |
| `POLL_INTERVAL` | `300` | GitHub API polling interval (seconds) |
| `MCP_MODE` | `false` | Set to `true` to run MCP server instead of API |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Creating GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select appropriate scopes (public repo access is sufficient)
4. Copy the generated token

**Note**: The application works without a token but has much lower rate limits (60 requests/hour vs 5000/hour).

## Docker Deployment

### Using Docker Compose (Recommended)

```yaml
# docker-compose.yml
version: '3.8'
services:
  github-events-monitor:
    image: sparesparrow/github-events-monitor:latest
    ports:
      - "8000:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - API_PORT=8000
      - POLL_INTERVAL=300
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Docker Directly

```bash
# Basic usage
docker run -d \
  --name github-events-monitor \
  -p 8000:8000 \
  -e GITHUB_TOKEN=your_token \
  sparesparrow/github-events-monitor:latest

# With persistent storage
docker run -d \
  --name github-events-monitor \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e GITHUB_TOKEN=your_token \
  -e DATABASE_PATH=/app/data/github_events.db \
  sparesparrow/github-events-monitor:latest

# Custom configuration
docker run -d \
  --name github-events-monitor \
  -p 18000:8080 \
  -e API_PORT=8080 \
  -e POLL_INTERVAL=600 \
  -e GITHUB_TOKEN=your_token \
  --restart unless-stopped \
  sparesparrow/github-events-monitor:latest
```

### MCP Server Mode

```bash
# Run as MCP server instead of REST API
docker run -d \
  --name github-events-mcp \
  -e GITHUB_TOKEN=your_token \
  -e MCP_MODE=true \
  sparesparrow/github-events-monitor:latest
```

## Production Deployment

### System Requirements

**Minimum**:
- CPU: 1 core
- Memory: 512MB RAM
- Storage: 1GB disk space
- Network: Internet access for GitHub API

**Recommended**:
- CPU: 2 cores
- Memory: 1GB RAM
- Storage: 5GB disk space
- Network: Stable internet connection

### Production Docker Compose

```yaml
version: '3.8'
services:
  github-events-monitor:
    image: sparesparrow/github-events-monitor:0.2.1
    ports:
      - "8000:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - API_PORT=8000
      - POLL_INTERVAL=300
      - LOG_LEVEL=INFO
      - DATABASE_PATH=/app/data/github_events.db
    volumes:
      - github-events-data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - github-events-monitor
    restart: unless-stopped

volumes:
  github-events-data:
```

### Nginx Configuration (Optional)

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream github-events {
        server github-events-monitor:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://github-events;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## Kubernetes Deployment

### Basic Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-events-monitor
  labels:
    app: github-events-monitor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: github-events-monitor
  template:
    metadata:
      labels:
        app: github-events-monitor
    spec:
      containers:
      - name: github-events-monitor
        image: sparesparrow/github-events-monitor:0.2.1
        ports:
        - containerPort: 8000
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-token-secret
              key: token
        - name: API_PORT
          value: "8000"
        - name: POLL_INTERVAL
          value: "300"
        - name: DATABASE_PATH
          value: "/app/data/github_events.db"
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: github-events-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: github-events-service
spec:
  selector:
    app: github-events-monitor
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: github-events-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi

---
apiVersion: v1
kind: Secret
metadata:
  name: github-token-secret
type: Opaque
data:
  token: <base64-encoded-github-token>
```

```bash
# Deploy to Kubernetes
kubectl apply -f k8s-deployment.yaml

# Check deployment status
kubectl get pods -l app=github-events-monitor
kubectl get services

# View logs
kubectl logs -l app=github-events-monitor -f
```

## Local Development Setup

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

### Setup Steps

```bash
# Clone repository
git clone https://github.com/sparesparrow/github-events.git
cd github-events

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.template .env
# Edit .env and add your configuration

# Run tests to verify setup
pytest

# Start development server
python -m github_events_monitor.api
```

### Development Environment Variables

```bash
# .env for development
GITHUB_TOKEN=your_github_token_here
DATABASE_PATH=./dev_github_events.db
API_HOST=127.0.0.1
API_PORT=8000
POLL_INTERVAL=60
LOG_LEVEL=DEBUG
```

### Development Tools

```bash
# Run tests with coverage
pytest --cov=src/github_events_monitor

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Monitoring and Health Checks

### Health Endpoint

The application provides a health check endpoint at `/health`:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "database_path": "/app/data/github_events.db",
  "github_token_configured": true,
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

### Monitoring Integration

#### Prometheus Metrics (Future Enhancement)

```python
# Example metrics that could be added
from prometheus_client import Counter, Histogram, Gauge

events_collected = Counter('github_events_collected_total', 'Total events collected', ['event_type'])
api_request_duration = Histogram('api_request_duration_seconds', 'API request duration')
last_poll_timestamp = Gauge('last_github_poll_timestamp', 'Timestamp of last GitHub API poll')
```

#### Log Monitoring

The application uses structured JSON logging. Key log events:

- Event collection success/failure
- API request patterns
- Database operations
- Rate limiting events
- Error conditions

## Troubleshooting

### Common Issues

#### 1. Rate Limiting
```bash
# Check current rate limit status
curl http://localhost:8000/health

# Symptoms: HTTP 403 responses, slower event collection
# Solution: Add GITHUB_TOKEN or increase POLL_INTERVAL
```

#### 2. Database Issues
```bash
# Check database file permissions
ls -la github_events.db

# Symptoms: SQLite errors, missing data
# Solution: Ensure write permissions, check disk space
```

#### 3. Port Conflicts
```bash
# Check if port is in use
netstat -tulpn | grep :8000

# Solution: Change API_PORT environment variable
export API_PORT=8080
```

#### 4. Docker Issues
```bash
# Check container logs
docker logs github-events-monitor

# Check container status
docker ps -a

# Restart container
docker restart github-events-monitor
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Or in Docker
docker run -e LOG_LEVEL=DEBUG sparesparrow/github-events-monitor:latest
```

## Performance Tuning

### Database Optimization

```bash
# SQLite pragma settings for performance
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=memory;
```

### Memory Management

```bash
# Monitor memory usage
docker stats github-events-monitor

# Limit memory usage
docker run --memory=512m sparesparrow/github-events-monitor:latest
```

### API Performance

- Use connection pooling for high-concurrency scenarios
- Implement caching for frequently requested metrics
- Consider read replicas for query-heavy workloads

## Security Considerations

### Environment Security

```bash
# Use secrets management
kubectl create secret generic github-token --from-literal=token=your-token

# File permissions
chmod 600 .env
```

### Network Security

```bash
# Firewall rules (example for Ubuntu)
sudo ufw allow 8000/tcp
sudo ufw enable

# Docker network isolation
docker network create --driver bridge github-events-net
```

### Container Security

```bash
# Run as non-root user (already configured in Dockerfile)
USER 1000:1000

# Security scanning
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  anchore/grype:latest sparesparrow/github-events-monitor:latest
```

## Backup and Recovery

### Database Backup

```bash
# Backup SQLite database
sqlite3 github_events.db ".backup backup.db"

# Or copy file (when service is stopped)
cp github_events.db backup_$(date +%Y%m%d).db
```

### Configuration Backup

```bash
# Backup configuration
tar -czf config_backup.tar.gz .env docker-compose.yml
```

### Recovery

```bash
# Restore database
sqlite3 github_events.db ".restore backup.db"

# Restart service
docker-compose restart
```