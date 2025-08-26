"""
Unit tests for GitHub Events Collector

Tests the core functionality of event collection, storage, and metric calculations.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import aiosqlite

from ..collector import GitHubEventsCollector, GitHubEvent  # type: ignore


class TestGitHubEvent:
    """Test GitHubEvent data class"""
    
    def test_from_api_data(self):
        """Test creating GitHubEvent from API response data"""
        api_data = {
            "id": "38990681048",
            "type": "PullRequestEvent",
            "repo": {"name": "owner/repo"},
            "actor": {"login": "testuser"},
            "created_at": "2024-06-04T15:55:23Z",
            "payload": {"action": "opened", "number": 123}
        }
        
        event = GitHubEvent.from_api_data(api_data)
        
        assert event.id == "38990681048"
        assert event.event_type == "PullRequestEvent"
        assert event.repo_name == "owner/repo"
        assert event.actor_login == "testuser"
        assert event.payload == {"action": "opened", "number": 123}
        assert isinstance(event.created_at, datetime)
    
    def test_to_dict(self):
        """Test converting GitHubEvent to dictionary"""
        event = GitHubEvent(
            id="123",
            event_type="WatchEvent",
            repo_name="test/repo",
            actor_login="user",
            created_at=datetime.now(timezone.utc),
            payload={"action": "started"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["id"] == "123"
        assert event_dict["event_type"] == "WatchEvent"
        assert event_dict["repo_name"] == "test/repo"
        assert "created_at" in event_dict
        assert isinstance(event_dict["created_at"], str)


class TestGitHubEventsCollector:
    """Test GitHubEventsCollector class"""
    
    @pytest.fixture
    async def collector(self):
        """Create a collector with temporary database"""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        collector = GitHubEventsCollector(
            db_path=db_path,
            github_token="test_token"
        )
        await collector.initialize_database()
        
        yield collector
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def sample_events_data(self):
        """Sample GitHub API events response data"""
        return [
            {
                "id": "1",
                "type": "WatchEvent",
                "repo": {"name": "test/repo1"},
                "actor": {"login": "user1"},
                "created_at": "2024-06-04T15:55:23Z",
                "payload": {"action": "started"}
            },
            {
                "id": "2",
                "type": "PullRequestEvent",
                "repo": {"name": "test/repo1"},
                "actor": {"login": "user2"},
                "created_at": "2024-06-04T15:56:23Z",
                "payload": {"action": "opened", "number": 1}
            },
            {
                "id": "3",
                "type": "IssuesEvent",
                "repo": {"name": "test/repo2"},
                "actor": {"login": "user3"},
                "created_at": "2024-06-04T15:57:23Z",
                "payload": {"action": "opened", "number": 1}
            },
            {
                "id": "4",
                "type": "PushEvent",  # This should be filtered out
                "repo": {"name": "test/repo1"},
                "actor": {"login": "user1"},
                "created_at": "2024-06-04T15:58:23Z",
                "payload": {"commits": []}
            }
        ]
    
    async def test_initialize_database(self, collector):
        """Test database initialization creates tables and indices"""
        # Check that tables exist
        async with aiosqlite.connect(collector.db_path) as db:
            cursor = await db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='events'
            """)
            tables = await cursor.fetchall()
            assert len(tables) == 1
            
            # Check indices exist
            cursor = await db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='events'
            """)
            indices = await cursor.fetchall()
            assert len(indices) >= 4  # We created 4 indices
    
    async def test_store_events(self, collector):
        """Test storing events in database"""
        events = [
            GitHubEvent(
                id="1",
                event_type="WatchEvent",
                repo_name="test/repo",
                actor_login="user1",
                created_at=datetime.now(timezone.utc),
                payload={"action": "started"}
            ),
            GitHubEvent(
                id="2",
                event_type="PullRequestEvent",
                repo_name="test/repo",
                actor_login="user2",
                created_at=datetime.now(timezone.utc),
                payload={"action": "opened", "number": 1}
            )
        ]
        
        stored_count = await collector.store_events(events)
        assert stored_count == 2
        
        # Verify events are in database
        async with aiosqlite.connect(collector.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM events")
            count = await cursor.fetchone()
            assert count[0] == 2
    
    async def test_store_events_deduplication(self, collector):
        """Test that duplicate events are not stored"""
        event = GitHubEvent(
            id="duplicate",
            event_type="WatchEvent",
            repo_name="test/repo",
            actor_login="user1",
            created_at=datetime.now(timezone.utc),
            payload={"action": "started"}
        )
        
        # Store same event twice
        count1 = await collector.store_events([event])
        count2 = await collector.store_events([event])
        
        assert count1 == 1
        assert count2 == 0  # Should be 0 due to deduplication
        
        # Verify only one event in database
        async with aiosqlite.connect(collector.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM events")
            count = await cursor.fetchone()
            assert count[0] == 1
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_events_success(self, mock_get, collector, sample_events_data):
        """Test successful event fetching from GitHub API"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_events_data
        mock_response.headers = {"ETag": "test-etag", "Last-Modified": "test-modified"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        events = await collector.fetch_events()
        
        # Should filter out PushEvent, leaving 3 events
        assert len(events) == 3
        assert all(isinstance(event, GitHubEvent) for event in events)
        assert events[0].event_type == "WatchEvent"
        assert events[1].event_type == "PullRequestEvent"
        assert events[2].event_type == "IssuesEvent"
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_events_rate_limited(self, mock_get, collector):
        """Test handling of rate limit (429 status)"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"X-RateLimit-Reset": str(int(datetime.now().timestamp()) + 1)}
        mock_get.return_value = mock_response
        
        events = await collector.fetch_events()
        
        assert events == []  # Should return empty list when rate limited
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_events_not_modified(self, mock_get, collector):
        """Test handling of 304 Not Modified response"""
        mock_response = Mock()
        mock_response.status_code = 304
        mock_get.return_value = mock_response
        
        events = await collector.fetch_events()
        
        assert events == []  # Should return empty list for 304
    
    async def test_get_event_counts_by_type(self, collector):
        """Test getting event counts by type with time offset"""
        now = datetime.now(timezone.utc)
        
        # Create test events with different timestamps
        events = [
            GitHubEvent("1", "WatchEvent", "test/repo", "user1", now - timedelta(minutes=5), {}),
            GitHubEvent("2", "WatchEvent", "test/repo", "user2", now - timedelta(minutes=3), {}),
            GitHubEvent("3", "PullRequestEvent", "test/repo", "user1", now - timedelta(minutes=2), {}),
            GitHubEvent("4", "IssuesEvent", "test/repo", "user1", now - timedelta(minutes=15), {}),  # Too old
        ]
        
        await collector.store_events(events)
        
        # Get counts for last 10 minutes
        counts = await collector.get_event_counts_by_type(10)
        
        assert counts["WatchEvent"] == 2
        assert counts["PullRequestEvent"] == 1
        assert counts["IssuesEvent"] == 0  # Too old to be included
    
    async def test_get_event_counts_invalid_offset(self, collector):
        """Test that invalid offset raises ValueError"""
        with pytest.raises(ValueError):
            await collector.get_event_counts_by_type(0)
        
        with pytest.raises(ValueError):
            await collector.get_event_counts_by_type(-5)
    
    async def test_get_avg_pr_interval(self, collector):
        """Test calculating average PR interval for a repository"""
        now = datetime.now(timezone.utc)
        
        # Create PR events with 1-hour intervals
        events = [
            GitHubEvent("1", "PullRequestEvent", "test/repo", "user1", 
                       now - timedelta(hours=3), {"action": "opened", "number": 1}),
            GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", 
                       now - timedelta(hours=2), {"action": "opened", "number": 2}),
            GitHubEvent("3", "PullRequestEvent", "test/repo", "user3", 
                       now - timedelta(hours=1), {"action": "opened", "number": 3}),
            # Add a closed event (should be ignored for interval calculation)
            GitHubEvent("4", "PullRequestEvent", "test/repo", "user1", 
                       now - timedelta(minutes=30), {"action": "closed", "number": 1}),
        ]
        
        await collector.store_events(events)
        
        result = await collector.get_avg_pr_interval("test/repo")
        
        assert result is not None
        assert result["repo_name"] == "test/repo"
        assert result["pr_count"] == 3  # Only opened PRs
        assert abs(result["avg_interval_seconds"] - 3600) < 10  # ~1 hour intervals
        assert abs(result["avg_interval_hours"] - 1.0) < 0.01
    
    async def test_get_avg_pr_interval_insufficient_data(self, collector):
        """Test that insufficient PR data returns None"""
        # Store only one PR event
        event = GitHubEvent("1", "PullRequestEvent", "test/repo", "user1", 
                           datetime.now(timezone.utc), {"action": "opened", "number": 1})
        await collector.store_events([event])
        
        result = await collector.get_avg_pr_interval("test/repo")
        
        assert result is None
    
    async def test_get_avg_pr_interval_no_data(self, collector):
        """Test that no PR data returns None"""
        result = await collector.get_avg_pr_interval("nonexistent/repo")
        assert result is None
    
    async def test_get_repository_activity_summary(self, collector):
        """Test getting repository activity summary"""
        now = datetime.now(timezone.utc)
        
        events = [
            GitHubEvent("1", "WatchEvent", "test/repo", "user1", now - timedelta(hours=1), {}),
            GitHubEvent("2", "PullRequestEvent", "test/repo", "user2", now - timedelta(hours=2), {}),
            GitHubEvent("3", "IssuesEvent", "test/repo", "user3", now - timedelta(hours=3), {}),
            # Event outside time window
            GitHubEvent("4", "WatchEvent", "test/repo", "user4", now - timedelta(hours=30), {}),
        ]
        
        await collector.store_events(events)
        
        result = await collector.get_repository_activity_summary("test/repo", hours=24)
        
        assert result["repo_name"] == "test/repo"
        assert result["hours"] == 24
        assert result["total_events"] == 3
        assert "activity" in result
        assert "WatchEvent" in result["activity"]
        assert "PullRequestEvent" in result["activity"]
        assert "IssuesEvent" in result["activity"]
    
    async def test_get_trending_repositories(self, collector):
        """Test getting trending repositories"""
        now = datetime.now(timezone.utc)
        
        events = [
            # repo1: 3 events
            GitHubEvent("1", "WatchEvent", "owner1/repo1", "user1", now - timedelta(hours=1), {}),
            GitHubEvent("2", "PullRequestEvent", "owner1/repo1", "user2", now - timedelta(hours=2), {}),
            GitHubEvent("3", "IssuesEvent", "owner1/repo1", "user3", now - timedelta(hours=3), {}),
            # repo2: 2 events
            GitHubEvent("4", "WatchEvent", "owner2/repo2", "user4", now - timedelta(hours=1), {}),
            GitHubEvent("5", "PullRequestEvent", "owner2/repo2", "user5", now - timedelta(hours=2), {}),
            # repo3: 1 event
            GitHubEvent("6", "IssuesEvent", "owner3/repo3", "user6", now - timedelta(hours=1), {}),
        ]
        
        await collector.store_events(events)
        
        trending = await collector.get_trending_repositories(hours=24, limit=3)
        
        assert len(trending) == 3
        assert trending[0]["repo_name"] == "owner1/repo1"  # Most active
        assert trending[0]["total_events"] == 3
        assert trending[1]["repo_name"] == "owner2/repo2"
        assert trending[1]["total_events"] == 2
        assert trending[2]["repo_name"] == "owner3/repo3"
        assert trending[2]["total_events"] == 1
    
    async def test_collect_and_store_integration(self, collector, sample_events_data):
        """Test complete collect and store workflow"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_events_data
            mock_response.headers = {"ETag": "test-etag", "Last-Modified": "test-modified"}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            # Run complete workflow
            stored_count = await collector.collect_and_store()
            
            # Should have filtered and stored 3 events (excluding PushEvent)
            assert stored_count == 3
            
            # Verify events are in database
            async with aiosqlite.connect(collector.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM events")
                count = await cursor.fetchone()
                assert count[0] == 3

# Test runner helper
def run_async_test(coro):
    """Helper to run async tests"""
    return asyncio.get_event_loop().run_until_complete(coro)

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
