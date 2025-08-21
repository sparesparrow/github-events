"""
Unit tests for GitHub Events Monitor MCP Server

Tests the MCP tools, resources, and prompts.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch

from ...mcp_server import (
    get_event_counts, get_avg_pr_interval, get_repository_activity,
    get_trending_repositories, collect_events_now, server_status,
    recent_events_by_type, analyze_repository_trends,
    create_monitoring_dashboard_config, repository_health_assessment
)
from ...collector import GitHubEventsCollector, GitHubEvent


class TestMCPTools:
    """Test MCP tool functions"""

    @pytest.fixture
    async def mock_collector(self):
        """Create mock collector for testing"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_path)

        collector = GitHubEventsCollector(db_path=db_path)
        await collector.initialize_database()

        # Mock global collector
        with patch('github_events_monitor.mcp_server.collector', collector):
            yield collector

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    async def test_get_event_counts_success(self, mock_collector):
        """Test get_event_counts MCP tool"""
        # Setup test data
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "WatchEvent", "test/repo", "user1", now - timedelta(minutes=5), {}),
            GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", now - timedelta(minutes=3), {}),
        ]
        await mock_collector.store_events(events)

        result = await get_event_counts(10)

        assert result["success"] is True
        assert result["offset_minutes"] == 10
        assert result["total_events"] == 2
        assert result["counts"]["WatchEvent"] == 1
        assert result["counts"]["PullRequestEvent"] == 1
        assert result["counts"]["IssuesEvent"] == 0
        assert "timestamp" in result

    async def test_get_event_counts_invalid_offset(self, mock_collector):
        """Test get_event_counts with invalid offset"""
        result = await get_event_counts(0)

        assert result["success"] is False
        assert "error" in result
        assert "positive" in result["error"]

    async def test_get_event_counts_no_collector(self):
        """Test get_event_counts when collector is not initialized"""
        with patch('github_events_monitor.mcp_server.collector', None):
            result = await get_event_counts(10)

            assert "error" in result
            assert "not initialized" in result["error"]

    async def test_get_avg_pr_interval_success(self, mock_collector):
        """Test get_avg_pr_interval MCP tool"""
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "PullRequestEvent", "test/repo", "user1", 
                       now - timedelta(hours=2), {"action": "opened", "number": 1}),
            GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", 
                       now - timedelta(hours=1), {"action": "opened", "number": 2}),
        ]
        await mock_collector.store_events(events)

        result = await get_avg_pr_interval("test/repo")

        assert result["success"] is True
        assert result["repo_name"] == "test/repo"
        assert result["pr_count"] == 2
        assert result["avg_interval_seconds"] is not None
        assert "interpretation" in result
        assert "frequency_description" in result["interpretation"]
        assert "activity_level" in result["interpretation"]

    async def test_get_avg_pr_interval_insufficient_data(self, mock_collector):
        """Test get_avg_pr_interval with insufficient data"""
        # Store only one PR
        event = GitHubEvent("1", "PullRequestEvent", "test/repo", "user1", 
                           datetime.now(timezone.utc), {"action": "opened", "number": 1})
        await mock_collector.store_events([event])

        result = await get_avg_pr_interval("test/repo")

        assert result["success"] is True
        assert result["pr_count"] == 0
        assert "Insufficient data" in result["message"]

    async def test_get_repository_activity_success(self, mock_collector):
        """Test get_repository_activity MCP tool"""
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "WatchEvent", "test/repo", "user1", now - timedelta(hours=1), {}),
            GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", now - timedelta(hours=2), {}),
        ]
        await mock_collector.store_events(events)

        result = await get_repository_activity("test/repo", 24)

        assert result["success"] is True
        assert result["repo_name"] == "test/repo"
        assert result["hours"] == 24
        assert result["total_events"] == 2
        assert "insights" in result
        assert "activity_rate_per_hour" in result["insights"]
        assert "most_common_event" in result["insights"]
        assert "activity_assessment" in result["insights"]

    async def test_get_trending_repositories_success(self, mock_collector):
        """Test get_trending_repositories MCP tool"""
        now = datetime.now(timezone.utc)
        events = [
            GitHubEvent("1", "WatchEvent", "repo1/test", "user1", now - timedelta(hours=1), {}),
            GitHubEvent("2", "PullRequestEvent", "repo2/test", "user2", now - timedelta(hours=1), {}),
        ]
        await mock_collector.store_events(events)

        result = await get_trending_repositories(24, 10)

        assert result["success"] is True
        assert result["hours"] == 24
        assert result["limit"] == 10
        assert len(result["repositories"]) <= 2
        assert result["total_found"] == len(result["repositories"])
        assert "timestamp" in result

    async def test_collect_events_now_success(self, mock_collector):
        """Test collect_events_now MCP tool"""
        with patch.object(mock_collector, 'collect_and_store', return_value=5) as mock_collect:
            result = await collect_events_now(10)

            assert result["success"] is True
            assert result["events_collected"] == 5
            assert result["limit"] == 10
            assert "timestamp" in result
            mock_collect.assert_called_once_with(10)


class TestMCPResources:
    """Test MCP resource functions"""

    @pytest.fixture
    async def mock_collector(self):
        """Create mock collector for testing"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_path)

        collector = GitHubEventsCollector(db_path=db_path)
        await collector.initialize_database()

        with patch('github_events_monitor.mcp_server.collector', collector):
            yield collector

        if os.path.exists(db_path):
            os.unlink(db_path)

    async def test_server_status_success(self, mock_collector):
        """Test server_status MCP resource"""
        status_json = await server_status()

        import json
        status_data = json.loads(status_json)

        assert status_data["status"] == "running"
        assert "database_path" in status_data
        assert "github_token_configured" in status_data
        assert "poll_interval_seconds" in status_data
        assert "monitored_events" in status_data
        assert "last_updated" in status_data

    async def test_server_status_no_collector(self):
        """Test server_status when collector is not initialized"""
        with patch('github_events_monitor.mcp_server.collector', None):
            status_json = await server_status()

            import json
            status_data = json.loads(status_json)

            assert status_data["status"] == "error"
            assert "not initialized" in status_data["message"]

    async def test_recent_events_by_type_valid(self, mock_collector):
        """Test recent_events_by_type with valid event type"""
        result_json = await recent_events_by_type("WatchEvent")

        import json
        result_data = json.loads(result_json)

        assert result_data["event_type"] == "WatchEvent"
        assert "timestamp" in result_data

    async def test_recent_events_by_type_invalid(self, mock_collector):
        """Test recent_events_by_type with invalid event type"""
        result_json = await recent_events_by_type("InvalidEvent")

        import json
        result_data = json.loads(result_json)

        assert "error" in result_data
        assert "Invalid event type" in result_data["error"]


class TestMCPPrompts:
    """Test MCP prompt functions"""

    @pytest.fixture
    async def mock_data(self):
        """Setup mock data for prompt tests"""
        with patch('github_events_monitor.mcp_server.get_avg_pr_interval') as mock_pr, \
             patch('github_events_monitor.mcp_server.get_repository_activity') as mock_activity, \
             patch('github_events_monitor.mcp_server.get_trending_repositories') as mock_trending:

            # Mock PR interval data
            mock_pr.return_value = {
                "success": True,
                "repo_name": "test/repo",
                "pr_count": 10,
                "avg_interval_hours": 24.5
            }

            # Mock activity data
            mock_activity.return_value = {
                "success": True,
                "repo_name": "test/repo",
                "hours": 168,
                "total_events": 50,
                "activity": {
                    "WatchEvent": {"count": 20},
                    "PullRequestEvent": {"count": 15},
                    "IssuesEvent": {"count": 15}
                }
            }

            # Mock trending data
            mock_trending.return_value = {
                "success": True,
                "repositories": [
                    {"repo_name": "popular/repo", "total_events": 100}
                ]
            }

            yield

    async def test_analyze_repository_trends(self, mock_data):
        """Test analyze_repository_trends prompt"""
        prompt = await analyze_repository_trends("test/repo")

        assert "test/repo" in prompt
        assert "Pull Request Frequency" in prompt
        assert "Recent Activity" in prompt
        assert "Repository Health" in prompt
        assert "Development Velocity" in prompt
        assert "Community Engagement" in prompt
        assert "Trends and Patterns" in prompt
        assert "Recommendations" in prompt

    async def test_create_monitoring_dashboard_config(self, mock_data):
        """Test create_monitoring_dashboard_config prompt"""
        prompt = await create_monitoring_dashboard_config(24)

        assert "monitoring dashboard" in prompt
        assert "Key Metrics Panels" in prompt
        assert "Alert Configurations" in prompt
        assert "Visualization Requirements" in prompt
        assert "Dashboard Layout" in prompt
        assert "Refresh and Update Strategy" in prompt

    async def test_repository_health_assessment(self, mock_data):
        """Test repository_health_assessment prompt"""
        prompt = await repository_health_assessment("test/repo")

        assert "test/repo" in prompt
        assert "Repository Metrics Summary" in prompt
        assert "Assessment Framework" in prompt
        assert "Development Velocity" in prompt
        assert "Community Engagement" in prompt
        assert "Project Sustainability" in prompt
        assert "Operational Health" in prompt
        assert "Risk Factors" in prompt


# Integration tests
class TestMCPIntegration:
    """Integration tests for MCP server"""

    @pytest.fixture
    async def real_collector(self):
        """Create real collector with test data"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)

        collector = GitHubEventsCollector(db_path=db_path)
        await collector.initialize_database()

        # Add test data
        now = datetime.now(timezone.utc)
        events = []

        # Add PR events for interval testing
        for i in range(5):
            events.append(GitHubEvent(
                id=f"pr_{i}",
                event_type="PullRequestEvent",
                repo_name="test/repo",
                actor_login=f"user{i}",
                created_at=now - timedelta(hours=i),
                payload={"action": "opened", "number": i + 1}
            ))

        # Add other events
        for i in range(10):
            events.append(GitHubEvent(
                id=f"watch_{i}",
                event_type="WatchEvent",
                repo_name="test/repo",
                actor_login=f"user{i}",
                created_at=now - timedelta(minutes=i * 10),
                payload={"action": "started"}
            ))

        await collector.store_events(events)

        with patch('github_events_monitor.mcp_server.collector', collector):
            yield collector

        if os.path.exists(db_path):
            os.unlink(db_path)

    async def test_complete_workflow(self, real_collector):
        """Test complete MCP workflow with real data"""
        # Test event counts
        counts_result = await get_event_counts(60)
        assert counts_result["success"] is True
        assert counts_result["total_events"] > 0

        # Test PR intervals
        pr_result = await get_avg_pr_interval("test/repo")
        assert pr_result["success"] is True
        assert pr_result["pr_count"] == 5

        # Test repository activity
        activity_result = await get_repository_activity("test/repo", 24)
        assert activity_result["success"] is True
        assert activity_result["total_events"] > 0

        # Test trending repositories
        trending_result = await get_trending_repositories(24, 5)
        assert trending_result["success"] is True
        assert len(trending_result["repositories"]) > 0

        # Test server status
        status_json = await server_status()
        import json
        status_data = json.loads(status_json)
        assert status_data["status"] == "running"

        # Test prompts use the data
        analysis_prompt = await analyze_repository_trends("test/repo")
        assert "5 PRs tracked" in analysis_prompt

        dashboard_prompt = await create_monitoring_dashboard_config(24)
        assert "monitoring dashboard" in dashboard_prompt.lower()

        health_prompt = await repository_health_assessment("test/repo")
        assert "5" in health_prompt  # Should include PR count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
