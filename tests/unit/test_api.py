"""
Unit tests for GitHub Events Monitor API

Tests the FastAPI endpoints for GitHub Events monitoring.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from fastapi import status
import httpx

from github_events_monitor.api import app, collector_instance
from github_events_monitor.collector import GitHubEventsCollector, GitHubEvent
from github_events_monitor.services import MetricsService, VisualizationService, EventsRepository, HealthReporter


class TestAPI:
	"""Test FastAPI endpoints"""
	
	@pytest.fixture
	def client(self):
		"""Create test client"""
		return TestClient(app)
	
	@pytest.fixture
	async def mock_collector(self):
		"""Create mock collector for testing"""
		# Create temporary database
		db_fd, db_path = tempfile.mkstemp(suffix='.db')
		os.close(db_fd)
		
		collector = GitHubEventsCollector(db_path=db_path)
		await collector.initialize_database()
		
		# Mock the global collector instance
		with patch('github_events_monitor.api.collector_instance', collector):
			yield collector
		
		# Cleanup
		if os.path.exists(db_path):
			os.unlink(db_path)
	
	@pytest.fixture
	async def mock_services(self):
		"""Create mock services for testing"""
		# Create temporary database
		db_fd, db_path = tempfile.mkstemp(suffix='.db')
		os.close(db_fd)
		
		collector = GitHubEventsCollector(db_path=db_path)
		await collector.initialize_database()
		
		# Create service instances
		repository = EventsRepository(db_path)
		metrics_service = MetricsService(repository)
		visualization_service = VisualizationService(repository)
		health_reporter = HealthReporter(repository)
		
		# Mock all the global instances
		with patch('github_events_monitor.api.collector_instance', collector), \
			 patch('github_events_monitor.api.repository_instance', repository), \
			 patch('github_events_monitor.api.metrics_service', metrics_service), \
			 patch('github_events_monitor.api.visualization_service', visualization_service), \
			 patch('github_events_monitor.api.health_reporter', health_reporter):
			yield {
				'collector': collector,
				'repository': repository,
				'metrics_service': metrics_service,
				'visualization_service': visualization_service,
				'health_reporter': health_reporter
			}
		
		# Cleanup
		if os.path.exists(db_path):
			os.unlink(db_path)
	
	async def test_health_check(self, client, mock_services):
		"""Test health check endpoint"""
		response = client.get("/health")
		
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert data["status"] == "healthy"
		assert "database_path" in data
		assert "github_token_configured" in data
		assert "timestamp" in data
	
	async def test_get_event_counts_success(self, client, mock_services):
		"""Test event counts endpoint with valid data"""
		now = datetime.now(timezone.utc)
		events = [
			GitHubEvent("1", "WatchEvent", "test/repo", "user1", now - timedelta(minutes=5), {}),
			GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", now - timedelta(minutes=3), {}),
			GitHubEvent("3", "IssuesEvent", "test/repo", "user3", now - timedelta(minutes=2), {}),
		]
		await mock_services['collector'].store_events(events)
		
		response = client.get("/metrics/event-counts?offset_minutes=10")
		
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert data["offset_minutes"] == 10
		assert data["total_events"] == 3
		assert data["counts"]["WatchEvent"] == 1
		assert data["counts"]["PullRequestEvent"] == 1
		assert data["counts"]["IssuesEvent"] == 1
		assert "timestamp" in data
	
	def test_get_event_counts_invalid_offset(self, client):
		"""Test event counts endpoint with invalid offset"""
		response = client.get("/metrics/event-counts?offset_minutes=0")
		assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
		
		response = client.get("/metrics/event-counts?offset_minutes=-5")
		assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
	
	def test_get_event_counts_missing_param(self, client):
		"""Test event counts endpoint without required parameter"""
		response = client.get("/metrics/event-counts")
		assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
	
	async def test_get_pr_interval_success(self, client, mock_services):
		"""Test PR interval endpoint with valid data"""
		now = datetime.now(timezone.utc)
		events = [
			GitHubEvent("1", "PullRequestEvent", "test/repo", "user1", 
						now - timedelta(hours=2), {"action": "opened", "number": 1}),
			GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", 
						now - timedelta(hours=1), {"action": "opened", "number": 2}),
		]
		await mock_services['collector'].store_events(events)
		
		response = client.get("/metrics/pr-interval?repo=test/repo")
		
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert data["repo_name"] == "test/repo"
		assert data["pr_count"] == 2
		assert data["avg_interval_seconds"] is not None
		assert data["avg_interval_hours"] is not None
	
	async def test_get_pr_interval_no_data(self, client, mock_services):
		"""Test PR interval endpoint with no data"""
		response = client.get("/metrics/pr-interval?repo=nonexistent/repo")
		
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert data["repo_name"] == "nonexistent/repo"
		assert data["pr_count"] == 0
		assert data["avg_interval_seconds"] is None
	
	def test_get_pr_interval_missing_param(self, client):
		"""Test PR interval endpoint without required parameter"""
		response = client.get("/metrics/pr-interval")
		assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
	
	async def test_get_repository_activity_success(self, client, mock_services):
		"""Test repository activity endpoint"""
		now = datetime.now(timezone.utc)
		events = [
			GitHubEvent("1", "WatchEvent", "test/repo", "user1", now - timedelta(hours=1), {}),
			GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", now - timedelta(hours=2), {}),
		]
		await mock_services['collector'].store_events(events)
		
		response = client.get("/metrics/repository-activity?repo=test/repo&hours=24")
		
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert data["repo_name"] == "test/repo"
		assert data["hours"] == 24
		assert data["total_events"] == 2
		assert "activity" in data
		assert "timestamp" in data
	
	async def test_get_trending_repositories_success(self, client, mock_services):
		"""Test trending repositories endpoint"""
		now = datetime.now(timezone.utc)
		events = [
			GitHubEvent("1", "WatchEvent", "test/repo1", "user1", now - timedelta(hours=1), {}),
			GitHubEvent("2", "WatchEvent", "test/repo1", "user2", now - timedelta(hours=1), {}),
			GitHubEvent("3", "WatchEvent", "test/repo2", "user3", now - timedelta(hours=1), {}),
		]
		await mock_services['collector'].store_events(events)
		
		response = client.get("/metrics/trending?hours=24&limit=5")
		
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert data["hours"] == 24
		assert len(data["repositories"]) == 2  # We have 2 unique repos
		assert "timestamp" in data
	
	async def test_manual_collect(self, client, mock_services):
		"""Test manual collection trigger endpoint"""
		with patch.object(mock_services['collector'], 'collect_and_store', return_value=5) as mock_collect:
			response = client.post("/collect?limit=10")
			
			assert response.status_code == status.HTTP_200_OK
			data = response.json()
			assert data["message"] == "Collection started"
			assert data["limit"] == 10
	
	def test_manual_collect_no_limit(self, client):
		"""Test manual collection without limit parameter"""
		response = client.post("/collect")
		
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert data["message"] == "Collection started"
		assert data["limit"] is None
	
	async def test_visualization_trending_chart(self, client, mock_services):
		"""Test trending chart visualization endpoint"""
		# Setup some test data
		now = datetime.now(timezone.utc)
		events = [
			GitHubEvent("1", "WatchEvent", "popular/repo", "user1", now - timedelta(hours=1), {}),
			GitHubEvent("2", "PullRequestEvent", "popular/repo", "user2", now - timedelta(hours=1), {}),
			GitHubEvent("3", "IssuesEvent", "popular/repo", "user3", now - timedelta(hours=1), {}),
		]
		await mock_services['collector'].store_events(events)
		
		response = client.get("/visualization/trending-chart?hours=24&limit=5&format=png")
		
		assert response.status_code == status.HTTP_200_OK
		assert response.headers["content-type"] == "image/png"
	
	async def test_visualization_trending_chart_no_data(self, client, mock_services):
		"""Test trending chart with no data"""
		response = client.get("/visualization/trending-chart?hours=24&limit=5")
		
		assert response.status_code == status.HTTP_404_NOT_FOUND
		data = response.json()
		assert "No data found" in data["detail"]
	
	def test_visualization_trending_chart_invalid_format(self, client):
		"""Test trending chart with invalid format"""
		response = client.get("/visualization/trending-chart?format=invalid")
		assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
	
	def test_not_found_endpoint(self, client):
		"""Test accessing non-existent endpoint"""
		response = client.get("/non-existent-endpoint")
		assert response.status_code == status.HTTP_404_NOT_FOUND


