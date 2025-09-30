# Docker Usage Guide - GitHub Events Monitor

## 🐳 Published Docker Images

The GitHub Events Monitor is now available as Docker images on Docker Hub:

- **Latest**: `sparesparrow/github-events-monitor:latest`
- **Version 0.2.1**: `sparesparrow/github-events-monitor:0.2.1`

## 🚀 Quick Start

### Basic Usage

```bash
# Run with default settings
docker run -d \
  --name github-events-monitor \
  -p 8000:8000 \
  -e GITHUB_TOKEN=your_github_token \
  sparesparrow/github-events-monitor:latest
```

### With Custom Configuration

```bash
# Run with custom settings
docker run -d \
  --name github-events-monitor \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e GITHUB_TOKEN=your_github_token \
  -e API_PORT=8000 \
  -e POLL_INTERVAL=300 \
  -e DATABASE_PATH=/app/data/github_events.db \
  sparesparrow/github-events-monitor:latest
```

## 📊 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | None | GitHub Personal Access Token (recommended) |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `DATABASE_PATH` | `/app/data/github_events.db` | SQLite database path |
| `POLL_INTERVAL` | `300` | GitHub API polling interval (seconds) |
| `MCP_MODE` | `false` | Set to `true` to run MCP server instead of REST API |

## 🎯 Usage Examples

### 1. REST API Mode (Default)

```bash
# Start the REST API server
docker run -d \
  --name github-events-api \
  -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_your_token_here \
  sparesparrow/github-events-monitor:latest

# Test the API
curl http://localhost:8000/health
curl http://localhost:8000/metrics/event-counts?offset_minutes=60
```

### 2. MCP Server Mode

```bash
# Start the MCP server
docker run -d \
  --name github-events-mcp \
  -e GITHUB_TOKEN=ghp_your_token_here \
  -e MCP_MODE=true \
  sparesparrow/github-events-monitor:latest
```

### 3. With Persistent Storage

```bash
# Create data directory
mkdir -p ./github-events-data

# Run with persistent storage
docker run -d \
  --name github-events-monitor \
  -p 8000:8000 \
  -v $(pwd)/github-events-data:/app/data \
  -e GITHUB_TOKEN=ghp_your_token_here \
  sparesparrow/github-events-monitor:latest
```

### 4. Using Docker Compose

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
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

```bash
# Start with docker-compose
docker-compose up -d
```

## 🔍 Testing the Container

### Health Check

```bash
# Check if the container is healthy
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database_path": "/app/data/github_events.db",
  "github_token_configured": true,
  "timestamp": "2025-08-21T19:46:37.550577+00:00"
}
```

### Collect Events

```bash
# Manually trigger event collection
curl -X POST http://localhost:8000/collect
```

### Get Metrics

```bash
# Get event counts for the last 60 minutes
curl "http://localhost:8000/metrics/event-counts?offset_minutes=60"

# Get PR intervals for a repository
curl "http://localhost:8000/metrics/pr-interval?repo=owner/repo"

# Get trending repositories
curl "http://localhost:8000/metrics/trending?hours=24&limit=10"
```

### Visualization

```bash
# Get trending chart
curl "http://localhost:8000/visualization/trending-chart?hours=24&limit=5&format=png" \
  --output trending_chart.png
```

## 🛠️ Development and Debugging

### View Logs

```bash
# View container logs
docker logs github-events-monitor

# Follow logs in real-time
docker logs -f github-events-monitor
```

### Interactive Shell

```bash
# Access container shell
docker exec -it github-events-monitor /bin/bash
```

### Inspect Container

```bash
# Check container status
docker ps

# Inspect container details
docker inspect github-events-monitor
```

## 🔧 Advanced Configuration

### Custom Port Mapping

```bash
# Map to different host port
docker run -d \
  --name github-events-monitor \
  -p 18000:8000 \
  -e API_PORT=8000 \
  -e GITHUB_TOKEN=your_token \
  sparesparrow/github-events-monitor:latest
```

### Multiple Instances

```bash
# Run multiple instances with different ports
docker run -d --name github-events-1 -p 8001:8000 -e GITHUB_TOKEN=your_token sparesparrow/github-events-monitor:latest
docker run -d --name github-events-2 -p 8002:8000 -e GITHUB_TOKEN=your_token sparesparrow/github-events-monitor:latest
```

### Resource Limits

```bash
# Run with resource limits
docker run -d \
  --name github-events-monitor \
  -p 8000:8000 \
  --memory=512m \
  --cpus=1.0 \
  -e GITHUB_TOKEN=your_token \
  sparesparrow/github-events-monitor:latest
```

## 🔒 Security Considerations

### GitHub Token Security

```bash
# Use environment file for sensitive data
echo "GITHUB_TOKEN=ghp_your_token_here" > .env

# Run with environment file
docker run -d \
  --name github-events-monitor \
  -p 8000:8000 \
  --env-file .env \
  sparesparrow/github-events-monitor:latest
```

### Network Security

```bash
# Run with custom network
docker network create github-events-network

docker run -d \
  --name github-events-monitor \
  --network github-events-network \
  -p 8000:8000 \
  -e GITHUB_TOKEN=your_token \
  sparesparrow/github-events-monitor:latest
```

## 📈 Monitoring and Health Checks

The container includes built-in health checks:

```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Health check endpoint: `http://localhost:8000/health`

## 🚀 Production Deployment

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
    volumes:
      - github-events-data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  github-events-data:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-events-monitor
spec:
  replicas: 1
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
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: github-events-pvc
```

## 🎉 Success!

Your GitHub Events Monitor is now running in Docker! 

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics/event-counts?offset_minutes=60

The container will automatically start collecting GitHub events and provide real-time metrics via the REST API.
