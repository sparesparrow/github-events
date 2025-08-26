# GitHub Events Monitor Scripts

This directory contains Python scripts designed for use in GitHub Actions workflows and automation.

## Available Scripts

### `manual_db_update.py`

Updates the database with events from specific repositories.

**Usage:**
```bash
python scripts/manual_db_update.py --repos "owner/repo1,owner/repo2" --limit 300
```

**Options:**
- `--repos`: Comma-separated list of repositories (owner/repo,owner/repo2)
- `--limit`: Maximum number of events to collect per repository (default: 300)
- `--db-path`: Database file path (default: from DATABASE_PATH env var)
- `--github-token`: GitHub API token (default: from GITHUB_TOKEN env var)

**Example in workflow:**
```yaml
- name: Update DB for specific repos
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    DATABASE_PATH: github_events.db
  run: |
    python scripts/manual_db_update.py --repos "${{ inputs.repositories }}" --limit 300
```

### `health_check.py`

Checks the health of the database and API.

**Usage:**
```bash
python scripts/health_check.py --db-path github_events.db
```

**Options:**
- `--db-path`: Database file path (default: from DATABASE_PATH env var)
- `--output`: Output format: json, text (default: text)
- `--exit-on-error`: Exit with error code if health check fails

**Example in workflow:**
```yaml
- name: Health Check
  env:
    DATABASE_PATH: github_events.db
  run: |
    python scripts/health_check.py --exit-on-error
```

### `export_metrics.py`

Exports various metrics from the database for reporting and analysis.

**Usage:**
```bash
python scripts/export_metrics.py --output metrics.json --hours 24
```

**Options:**
- `--output`: Output file path (default: stdout)
- `--db-path`: Database file path (default: from DATABASE_PATH env var)
- `--hours`: Hours to look back for metrics (default: 24)
- `--trending-limit`: Number of trending repositories to include (default: 10)
- `--repos`: Comma-separated list of specific repos to analyze

**Example in workflow:**
```yaml
- name: Export Metrics
  env:
    DATABASE_PATH: github_events.db
  run: |
    python scripts/export_metrics.py \
      --output daily_metrics.json \
      --hours 24 \
      --trending-limit 20
```

## Environment Variables

All scripts support these environment variables:

- `DATABASE_PATH`: Path to the SQLite database file
- `GITHUB_TOKEN`: GitHub API token for authentication
- `TARGET_REPOSITORIES`: Comma-separated list of repositories to monitor

## Integration with DatabaseManager

All scripts use the `DatabaseManager` class which provides:
- Centralized database initialization
- Access to all DAOs (SchemaDao, EventsWriteDao, AggregatesDao, EventsDaoFactory)
- Proper error handling and resource management

## Error Handling

Scripts are designed to:
- Exit with appropriate error codes for CI/CD integration
- Provide clear error messages
- Handle missing dependencies gracefully
- Support both interactive and automated usage

## Testing Scripts Locally

To test scripts locally:

1. Install the package in development mode:
   ```bash
   pip install -e .
   ```

2. Set up environment variables:
   ```bash
   export DATABASE_PATH=github_events.db
   export GITHUB_TOKEN=your_token_here
   ```

3. Run scripts:
   ```bash
   python scripts/health_check.py
   python scripts/export_metrics.py --output test_metrics.json
   ```
