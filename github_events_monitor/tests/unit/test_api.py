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

# Import our API
from ...api import app, collector_instance
from ...collector import GitHubEventsCollector, GitHubEvent


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
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "database_path" in data
        assert "github_token_configured" in data
        assert "timestamp" in data
    
    async def test_get_event_counts_success(self, client, mock_collector):
        """Test event counts endpoint with valid data"""
        # Setup test data
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "WatchEvent", "test/repo", "user1", now - timedelta(minutes=5), {}),
            GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", now - timedelta(minutes=3), {}),
            GitHubEvent("3", "IssuesEvent", "test/repo", "user3", now - timedelta(minutes=2), {}),
        ]
        await mock_collector.store_events(events)
        
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
    
    async def test_get_pr_interval_success(self, client, mock_collector):
        """Test PR interval endpoint with valid data"""
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "PullRequestEvent", "test/repo", "user1", 
                       now - timedelta(hours=2), {"action": "opened", "number": 1}),
            GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", 
                       now - timedelta(hours=1), {"action": "opened", "number": 2}),
        ]
        await mock_collector.store_events(events)
        
        response = client.get("/metrics/pr-interval?repo=test/repo")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["repo_name"] == "test/repo"
        assert data["pr_count"] == 2
        assert data["avg_interval_seconds"] is not None
        assert data["avg_interval_hours"] is not None
    
    async def test_get_pr_interval_no_data(self, client, mock_collector):
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
    
    async def test_get_repository_activity_success(self, client, mock_collector):
        """Test repository activity endpoint"""
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "WatchEvent", "test/repo", "user1", now - timedelta(hours=1), {}),
            GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", now - timedelta(hours=2), {}),
        ]
        await mock_collector.store_events(events)
        
        response = client.get("/metrics/repository-activity?repo=test/repo&hours=24")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["repo_name"] == "test/repo"
        assert data["hours"] == 24
        assert data["total_events"] == 2
        assert "activity" in data
    
    async def test_get_repository_activity_default_hours(self, client, mock_collector):
        """Test repository activity endpoint with default hours parameter"""
        response = client.get("/metrics/repository-activity?repo=test/repo")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["hours"] == 24  # Default value
    
    async def test_get_trending_repositories(self, client, mock_collector):
        """Test trending repositories endpoint"""
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "WatchEvent", "repo1/test", "user1", now - timedelta(hours=1), {}),
            GitHubEvent("2", "WatchEvent", "repo2/test", "user2", now - timedelta(hours=1), {}),
            GitHubEvent("3", "PullRequestEvent", "repo1/test", "user3", now - timedelta(hours=1), {}),
        ]
        await mock_collector.store_events(events)
        
        response = client.get("/metrics/trending?hours=24&limit=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["hours"] == 24
        assert len(data["repositories"]) <= 2  # We have 2 unique repos
        assert "timestamp" in data
    
    async def test_manual_collect(self, client, mock_collector):
        """Test manual collection trigger endpoint"""
        with patch.object(mock_collector, 'collect_and_store', return_value=5) as mock_collect:
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
    
    async def test_visualization_trending_chart(self, client, mock_collector):
        """Test trending chart visualization endpoint"""
        # Setup some test data
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "WatchEvent", "popular/repo", "user1", now - timedelta(hours=1), {}),
            GitHubEvent("2", "PullRequestEvent", "popular/repo", "user2", now - timedelta(hours=1), {}),
            GitHubEvent("3", "IssuesEvent", "popular/repo", "user3", now - timedelta(hours=1), {}),
        ]
        await mock_collector.store_events(events)
        
        response = client.get("/visualization/trending-chart?hours=24&limit=5&format=png")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "image/png"
    
    async def test_visualization_trending_chart_no_data(self, client, mock_collector):
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

# Integration tests that test the full request/response cycle
class TestAPIIntegration:
    """Integration tests for API endpoints"""
    
    @pytest.fixture
    async def real_collector(self):
        """Create a real collector with test database"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        collector = GitHubEventsCollector(db_path=db_path, github_token="test_token")
        await collector.initialize_database()
        
        yield collector
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @patch('httpx.AsyncClient.get')
    async def test_full_collection_workflow(self, mock_get, real_collector):
        """Test complete collection and API workflow"""
        # Mock GitHub API response
        sample_events = [
            {
                "id": "1",
                "type": "WatchEvent",
                "repo": {"name": "test/repo"},
                "actor": {"login": "user1"},
                "created_at": "2024-06-04T15:55:23Z",
                "payload": {"action": "started"}
            },
            {
                "id": "2", 
                "type": "PullRequestEvent",
                "repo": {"name": "test/repo"},
                "actor": {"login": "user2"},
                "created_at": "2024-06-04T15:56:23Z",
                "payload": {"action": "opened", "number": 1}
            }
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_events
        mock_response.headers = {"ETag": "test", "Last-Modified": "test"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Collect events
        count = await real_collector.collect_and_store()
        assert count == 2
        
        # Test metrics
        counts = await real_collector.get_event_counts_by_type(60)
        assert counts["WatchEvent"] == 1
        assert counts["PullRequestEvent"] == 1
        assert counts["IssuesEvent"] == 0
        
        # Test PR interval (should return None with only 1 PR)
        pr_result = await real_collector.get_avg_pr_interval("test/repo")
        assert pr_result is None  # Need at least 2 opened PRs
        
        # Test activity summary
        activity = await real_collector.get_repository_activity_summary("test/repo", 24)
        assert activity["total_events"] == 2
        assert activity["repo_name"] == "test/repo"

# Performance tests
class TestAPIPerformance:
    """Performance tests for API endpoints"""
    
    @pytest.fixture
    async def large_dataset_collector(self):
        """Create collector with large dataset for performance testing"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        collector = GitHubEventsCollector(db_path=db_path)
        await collector.initialize_database()
        
        # Create large dataset
        now = datetime.now(timezone.utc)
        events = []
        
        for i in range(1000):
            events.append(GitHubEvent(
                id=str(i),
                event_type=["WatchEvent", "PullRequestEvent", "IssuesEvent"][i % 3],
                repo_name=f"repo{i % 10}/test",
                actor_login=f"user{i % 50}",
                created_at=now - timedelta(hours=i % 48),
                payload={"action": "opened", "number": i} if i % 3 == 1 else {}
            ))
        
        await collector.store_events(events)
        
        yield collector
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    async def test_event_counts_performance(self, large_dataset_collector):
        """Test performance of event counts query with large dataset"""
        import time
        
        start_time = time.time()
        counts = await large_dataset_collector.get_event_counts_by_type(60)
        end_time = time.time()
        
        assert end_time - start_time < 1.0  # Should complete within 1 second
        assert sum(counts.values()) > 0
    
    async def test_trending_repositories_performance(self, large_dataset_collector):
        """Test performance of trending repositories query with large dataset"""
        import time
        
        start_time = time.time()
        trending = await large_dataset_collector.get_trending_repositories(24, 10)
        end_time = time.time()
        
        assert end_time - start_time < 1.0  # Should complete within 1 second
        assert len(trending) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
