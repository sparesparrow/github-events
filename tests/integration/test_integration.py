"""
Integration tests for GitHub Events Monitor

End-to-end tests that verify the complete system functionality
including GitHub API integration, database operations, and metrics calculation.
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient

from github_events_monitor.collector import GitHubEventsCollector, GitHubEvent
from github_events_monitor.api import app


class TestEndToEndWorkflow:
	"""Test complete end-to-end workflows"""
	
	@pytest.fixture
	async def collector_with_real_structure(self):
		"""Create collector with real GitHub Events API structure"""
		db_fd, db_path = tempfile.mkstemp(suffix='.db')
		os.close(db_fd)
		
		collector = GitHubEventsCollector(db_path=db_path, github_token="test_token")
		await collector.initialize_database()
		
		yield collector, db_path
		
		if os.path.exists(db_path):
			os.unlink(db_path)
	
	def get_sample_github_events(self):
		"""Get sample GitHub Events API response matching real structure"""
		return [
			{
				"id": "38990681048",
				"type": "PullRequestEvent",
				"actor": {
					"id": 158077861,
					"login": "gus-opentensor",
					"display_login": "gus-opentensor",
					"gravatar_id": "",
					"url": "https://api.github.com/users/gus-opentensor",
					"avatar_url": "https://avatars.githubusercontent.com/u/158077861?"
				},
				"repo": {
					"id": 283347912,
					"name": "opentensor/bittensor",
					"url": "https://api.github.com/repos/opentensor/bittensor"
				},
				"payload": {
					"action": "opened",
					"number": 1969,
					"pull_request": {
						"id": 1899182703,
						"state": "open",
						"title": "Feature: Add new functionality",
						"user": {
							"login": "gus-opentensor",
							"id": 158077861
						},
						"created_at": "2024-06-01T16:19:26Z",
						"updated_at": "2024-06-04T15:55:22Z"
					}
				},
				"public": True,
				"created_at": "2024-06-04T15:55:23Z"
			},
			{
				"id": "38990681049",
				"type": "WatchEvent",
				"actor": {
					"id": 12345,
					"login": "developer123",
					"display_login": "developer123"
				},
				"repo": {
					"id": 123456789,
					"name": "microsoft/vscode",
					"url": "https://api.github.com/repos/microsoft/vscode"
				},
				"payload": {
					"action": "started"
				},
				"public": True,
				"created_at": "2024-06-04T15:56:23Z"
			},
			{
				"id": "38990681050",
				"type": "IssuesEvent",
				"actor": {
					"id": 67890,
					"login": "bugfinder",
					"display_login": "bugfinder"
				},
				"repo": {
					"id": 987654321,
					"name": "facebook/react",
					"url": "https://api.github.com/repos/facebook/react"
				},
				"payload": {
					"action": "opened",
					"issue": {
						"id": 123456,
						"number": 100,
						"title": "Bug: Something is broken",
						"state": "open",
						"created_at": "2024-06-04T15:57:23Z"
					}
				},
				"public": True,
				"created_at": "2024-06-04T15:57:23Z"
			},
			{
				"id": "38990681051",
				"type": "PushEvent",
				"actor": {
					"id": 11111,
					"login": "coder",
					"display_login": "coder"
				},
				"repo": {
					"id": 111111,
					"name": "user/repo",
					"url": "https://api.github.com/repos/user/repo"
				},
				"payload": {
					"push_id": 18727054509,
					"size": 1,
					"distinct_size": 1,
					"ref": "refs/heads/master"
				},
				"public": True,
				"created_at": "2024-06-04T15:58:23Z"
			}
		]
	
	@patch('httpx.AsyncClient.get')
	async def test_github_api_integration(self, mock_get, collector_with_real_structure):
		"""Test integration with GitHub Events API using real event structure"""
		collector, db_path = collector_with_real_structure
		sample_events = self.get_sample_github_events()
		
		# Mock successful API response
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = sample_events
		mock_response.headers = {
			"ETag": '"abcd1234"',
			"Last-Modified": "Wed, 04 Jun 2024 15:55:23 GMT",
			"X-RateLimit-Remaining": "4999",
			"X-RateLimit-Reset": "1717520123"
		}
		mock_response.raise_for_status = Mock()
		mock_get.return_value = mock_response
		
		# Test complete collection workflow
		stored_count = await collector.collect_and_store()
		
		# Should have stored 3 events (filtered out PushEvent)
		assert stored_count == 3
		
		# Verify ETag and Last-Modified headers are stored
		assert collector.last_etag == '"abcd1234"'
		assert collector.last_modified == "Wed, 04 Jun 2024 15:55:23 GMT"
		
		# Verify events are correctly stored in database
		async with (collector._get_db_connection()) as db:
			cursor = await db.execute("""
				SELECT event_type, repo_name, actor_login, payload 
				FROM events ORDER BY created_at
			""")
			stored_events = await cursor.fetchall()
			
			assert len(stored_events) == 3
			
			# Verify first event (PullRequestEvent)
			pr_event = stored_events[0]
			assert pr_event[0] == "PullRequestEvent"
			assert pr_event[1] == "opentensor/bittensor"
			assert pr_event[2] == "gus-opentensor"
			payload = json.loads(pr_event[3])
			assert payload["action"] == "opened"
			assert payload["number"] == 1969
			
			# Verify second event (WatchEvent)
			watch_event = stored_events[1]
			assert watch_event[0] == "WatchEvent"
			assert watch_event[1] == "microsoft/vscode"
			assert watch_event[2] == "developer123"
			
			# Verify third event (IssuesEvent)
			issues_event = stored_events[2]
			assert issues_event[0] == "IssuesEvent"
			assert issues_event[1] == "facebook/react"
			assert issues_event[2] == "bugfinder"
	
	@patch('httpx.AsyncClient.get')
	async def test_rate_limiting_handling(self, mock_get, collector_with_real_structure):
		"""Test proper handling of GitHub API rate limiting"""
		collector, db_path = collector_with_real_structure
		
		# Mock rate limited response
		reset_time = int(datetime.now().timestamp()) + 2  # 2 seconds from now
		mock_response = Mock()
		mock_response.status_code = 429
		mock_response.headers = {
			"X-RateLimit-Remaining": "0",
			"X-RateLimit-Reset": str(reset_time),
			"Retry-After": "2"
		}
		mock_get.return_value = mock_response
		
		# Test that collector handles rate limiting gracefully
		import time
		start_time = time.time()
		events = await collector.fetch_events()
		end_time = time.time()
		
		# Should return empty list when rate limited
		assert events == []
		
	@patch('httpx.AsyncClient.get')
	async def test_conditional_requests(self, mock_get, collector_with_real_structure):
		"""Test that collector properly uses ETag and Last-Modified for conditional requests"""
		collector, db_path = collector_with_real_structure
		
		# First request - simulate getting data with ETag
		sample_events = self.get_sample_github_events()
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = sample_events
		mock_response.headers = {
			"ETag": '"first-etag"',
			"Last-Modified": "Wed, 04 Jun 2024 15:55:23 GMT"
		}
		mock_response.raise_for_status = Mock()
		mock_get.return_value = mock_response
		
		# First fetch
		await collector.fetch_events()
		
		# Verify headers are stored
		assert collector.last_etag == '"first-etag"'
		assert collector.last_modified == "Wed, 04 Jun 2024 15:55:23 GMT"
		
		# Second request - simulate 304 Not Modified
		mock_response.status_code = 304
		mock_get.return_value = mock_response
		
		# Second fetch
		events = await collector.fetch_events()
		
		# Should return empty list for 304
		assert events == []
		
		# Verify conditional headers were sent
		call_args = mock_get.call_args
		headers = call_args[1]['headers'] if len(call_args) > 1 else call_args.kwargs.get('headers', {})
		assert headers.get('If-None-Match') == '"first-etag"'
		assert headers.get('If-Modified-Since') == "Wed, 04 Jun 2024 15:55:23 GMT"
	
	async def test_comprehensive_metrics_calculation(self, collector_with_real_structure):
		"""Test comprehensive metrics calculation with realistic data"""
		collector, db_path = collector_with_real_structure
		
		# Create comprehensive test dataset
		now = datetime.now(timezone.utc)
		events = []
		
		# Repository 1: High activity
		repo1 = "microsoft/vscode"
		for i in range(20):
			# PR events every 2 hours
			if i < 10:
				events.append(GitHubEvent(
					id=f"pr_{repo1}_{i}",
					event_type="PullRequestEvent",
					repo_name=repo1,
					actor_login=f"contributor{i}",
					created_at=now - timedelta(hours=i * 2),
					payload={"action": "opened", "number": i + 1}
				))
			
			# Watch events every hour
			events.append(GitHubEvent(
				id=f"watch_{repo1}_{i}",
				event_type="WatchEvent", 
				repo_name=repo1,
				actor_login=f"watcher{i}",
				created_at=now - timedelta(hours=i),
				payload={"action": "started"}
			))
			
			# Issue events every 3 hours
			if i % 3 == 0:
				events.append(GitHubEvent(
					id=f"issue_{repo1}_{i}",
					event_type="IssuesEvent",
					repo_name=repo1,
					actor_login=f"reporter{i}",
					created_at=now - timedelta(hours=i * 3),
					payload={"action": "opened", "number": i // 3 + 1}
				))
		
		# Repository 2: Medium activity
		repo2 = "facebook/react"
		for i in range(5):
			events.append(GitHubEvent(
				id=f"pr_{repo2}_{i}",
				event_type="PullRequestEvent",
				repo_name=repo2,
				actor_login=f"react_dev{i}",
				created_at=now - timedelta(days=i),
				payload={"action": "opened", "number": i + 1}
			))
		
		# Store all events
		await collector.store_events(events)
		
		# Test event counts by type
		counts_1h = await collector.get_event_counts_by_type(60)  # Last hour
		counts_24h = await collector.get_event_counts_by_type(60 * 24)  # Last 24 hours
		
		assert counts_1h["WatchEvent"] >= 1
		assert counts_24h["PullRequestEvent"] >= 5
		assert sum(counts_24h.values()) > sum(counts_1h.values())
		
		# Test PR interval calculation
		pr_intervals_repo1 = await collector.get_avg_pr_interval(repo1)
		pr_intervals_repo2 = await collector.get_avg_pr_interval(repo2)
		
		assert pr_intervals_repo1 is not None
		assert pr_intervals_repo1["pr_count"] == 10
		assert pr_intervals_repo1["avg_interval_hours"] > 0
		
		assert pr_intervals_repo2 is not None
		assert pr_intervals_repo2["pr_count"] == 5
		# Should show daily intervals (24 hours)
		assert abs(pr_intervals_repo2["avg_interval_hours"] - 24.0) < 2.0
		
		# Test repository activity
		activity_repo1 = await collector.get_repository_activity_summary(repo1, 24)
		activity_repo2 = await collector.get_repository_activity_summary(repo2, 168)  # 1 week
		
		assert activity_repo1["total_events"] > activity_repo2["total_events"]
		assert "WatchEvent" in activity_repo1["activity"]
		assert "PullRequestEvent" in activity_repo1["activity"]
		
		# Test trending repositories
		trending = await collector.get_trending_repositories(24, 5)
		
		assert len(trending) >= 2
		assert trending[0]["repo_name"] == repo1  # Should be most active
		assert trending[0]["total_events"] > trending[1]["total_events"]
	

