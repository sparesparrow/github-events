FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Create directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV DATABASE_PATH=/app/data/github_events.db
ENV PYTHONPATH=/app/src
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

# Expose API port
EXPOSE 8000

# Health check respects API_PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request,sys;\nport=os.getenv('API_PORT','8000');\nurl=f'http://localhost:{port}/health';\ntry:\n    r=urllib.request.urlopen(url, timeout=5);\n    sys.exit(0 if r.status==200 else 1)\nexcept Exception:\n    sys.exit(1)"]

# Default command (can be overridden). Start REST API via entrypoint for robustness.
USER 1000:1000
CMD ["/app/entrypoint.sh"]


