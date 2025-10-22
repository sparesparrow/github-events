"""
Tests for github_utils module
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from github_events_monitor.utils.github_utils import (
    list_open_prs, create_github_pr, create_pr_with_gh_cli,
    get_current_user_login_from_token, parse_repository_url,
    get_default_branch, is_gh_cli_available, run_gh_command,
    get_gh_auth_status, get_repository_info, get_pr_info
)


class TestGitHubUtils:
    """Test cases for GitHub utilities."""
    
    @patch('github_events_monitor.utils.github_utils.requests')
    def test_list_open_prs_success(self, mock_requests):
        """Test successful PR listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"number": 1, "title": "Test PR", "user": {"login": "testuser"}}
        ]
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        result = list_open_prs("owner", "repo", "token")
        
        assert len(result) == 1
        assert result[0]["number"] == 1
        mock_requests.get.assert_called_once()
    
    @patch('github_events_monitor.utils.github_utils.requests', None)
    def test_list_open_prs_no_requests(self):
        """Test PR listing without requests library."""
        with pytest.raises(RuntimeError, match="requests library is required"):
            list_open_prs("owner", "repo")
    
    @patch('github_events_monitor.utils.github_utils.requests')
    def test_create_github_pr_success(self, mock_requests):
        """Test successful PR creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"url": "https://github.com/owner/repo/pull/1"}
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response
        
        result = create_github_pr("owner", "repo", "user:branch", "main", "Test PR", "Body", "token")
        
        assert result["url"] == "https://github.com/owner/repo/pull/1"
        mock_requests.post.assert_called_once()
    
    @patch('github_events_monitor.utils.github_utils.requests', None)
    def test_create_github_pr_no_requests(self):
        """Test PR creation without requests library."""
        with pytest.raises(RuntimeError, match="requests is required"):
            create_github_pr("owner", "repo", "user:branch", "main", "Test PR")
    
    @patch('github_events_monitor.utils.github_utils.shutil.which')
    @patch('subprocess.run')
    def test_create_pr_with_gh_cli_success(self, mock_run, mock_which):
        """Test successful PR creation with gh CLI."""
        mock_which.return_value = "/usr/bin/gh"
        mock_result = MagicMock()
        mock_result.stdout = '{"url": "https://github.com/owner/repo/pull/1"}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with patch('github_events_monitor.utils.github_utils.push_branch'):
            result = create_pr_with_gh_cli("origin", "branch", "main", "Test PR", "Body")
        
        assert result["url"] == "https://github.com/owner/repo/pull/1"
        mock_run.assert_called_once()
    
    @patch('github_events_monitor.utils.github_utils.shutil.which')
    def test_create_pr_with_gh_cli_not_available(self, mock_which):
        """Test PR creation when gh CLI is not available."""
        mock_which.return_value = None
        
        result = create_pr_with_gh_cli("origin", "branch", "main", "Test PR")
        
        assert result is None
    
    @patch('github_events_monitor.utils.github_utils.requests')
    def test_get_current_user_login_from_token_success(self, mock_requests):
        """Test successful user login retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"login": "testuser"}
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        
        result = get_current_user_login_from_token("token")
        
        assert result == "testuser"
        mock_requests.get.assert_called_once()
    
    @patch('github_events_monitor.utils.github_utils.requests')
    def test_get_current_user_login_from_token_failure(self, mock_requests):
        """Test user login retrieval failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response
        
        result = get_current_user_login_from_token("invalid_token")
        
        assert result is None
    
    @patch('github_events_monitor.utils.github_utils.requests', None)
    def test_get_current_user_login_from_token_no_requests(self):
        """Test user login retrieval without requests library."""
        result = get_current_user_login_from_token("token")
        
        assert result is None
    
    def test_parse_repository_url_https(self):
        """Test parsing HTTPS repository URL."""
        owner, repo = parse_repository_url("https://github.com/owner/repo")
        
        assert owner == "owner"
        assert repo == "repo"
    
    def test_parse_repository_url_ssh(self):
        """Test parsing SSH repository URL."""
        owner, repo = parse_repository_url("git@github.com:owner/repo.git")
        
        assert owner == "owner"
        assert repo == "repo"
    
    def test_parse_repository_url_invalid(self):
        """Test parsing invalid repository URL."""
        with pytest.raises(ValueError, match="Unable to parse repository URL"):
            parse_repository_url("invalid-url")
    
    @patch('github_events_monitor.utils.github_utils.requests')
    def test_get_repository_info_success(self, mock_requests):
        """Test successful repository info retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "repo", "owner": {"login": "owner"}}
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        result = get_repository_info("owner", "repo", "token")
        
        assert result["name"] == "repo"
        mock_requests.get.assert_called_once()
    
    @patch('github_events_monitor.utils.github_utils.requests', None)
    def test_get_repository_info_no_requests(self):
        """Test repository info retrieval without requests library."""
        with pytest.raises(RuntimeError, match="requests library is required"):
            get_repository_info("owner", "repo")
    
    @patch('github_events_monitor.utils.github_utils.get_repository_info')
    def test_get_default_branch(self, mock_get_repo_info):
        """Test getting default branch."""
        mock_get_repo_info.return_value = {"default_branch": "main"}
        
        result = get_default_branch("owner", "repo", "token")
        
        assert result == "main"
        mock_get_repo_info.assert_called_once_with("owner", "repo", "token")
    
    @patch('github_events_monitor.utils.github_utils.get_repository_info')
    def test_get_default_branch_fallback(self, mock_get_repo_info):
        """Test getting default branch with fallback."""
        mock_get_repo_info.return_value = {}
        
        result = get_default_branch("owner", "repo", "token")
        
        assert result == "main"
    
    @patch('github_events_monitor.utils.github_utils.shutil.which')
    def test_is_gh_cli_available_true(self, mock_which):
        """Test gh CLI availability when available."""
        mock_which.return_value = "/usr/bin/gh"
        
        result = is_gh_cli_available()
        
        assert result is True
    
    @patch('github_events_monitor.utils.github_utils.shutil.which')
    def test_is_gh_cli_available_false(self, mock_which):
        """Test gh CLI availability when not available."""
        mock_which.return_value = None
        
        result = is_gh_cli_available()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_run_gh_command_success(self, mock_run):
        """Test successful gh command execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = run_gh_command("pr list", capture=True)
        
        mock_run.assert_called_once()
        assert result == mock_result
    
    @patch('subprocess.run')
    def test_run_gh_command_failure(self, mock_run):
        """Test gh command execution failure."""
        mock_run.side_effect = Exception("Command failed")
        
        with pytest.raises(Exception):
            run_gh_command("invalid command")
    
    @patch('github_events_monitor.utils.github_utils.run_gh_command')
    def test_get_gh_auth_status_success(self, mock_run_gh):
        """Test successful gh auth status retrieval."""
        mock_result = MagicMock()
        mock_result.stdout = '{"authenticated": true, "user": "testuser"}'
        mock_run_gh.return_value = mock_result
        
        result = get_gh_auth_status()
        
        assert result["authenticated"] is True
        mock_run_gh.assert_called_once_with("auth status --json", capture=True)
    
    @patch('github_events_monitor.utils.github_utils.run_gh_command')
    def test_get_gh_auth_status_failure(self, mock_run_gh):
        """Test gh auth status retrieval failure."""
        mock_run_gh.side_effect = Exception("Auth failed")
        
        result = get_gh_auth_status()
        
        assert result["authenticated"] is False
        assert "error" in result
    
    @patch('github_events_monitor.utils.github_utils.requests')
    def test_get_pr_info_success(self, mock_requests):
        """Test successful PR info retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"number": 1, "title": "Test PR"}
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        result = get_pr_info("owner", "repo", 1, "token")
        
        assert result["number"] == 1
        assert result["title"] == "Test PR"
        mock_requests.get.assert_called_once()
    
    @patch('github_events_monitor.utils.github_utils.requests', None)
    def test_get_pr_info_no_requests(self):
        """Test PR info retrieval without requests library."""
        with pytest.raises(RuntimeError, match="requests library is required"):
            get_pr_info("owner", "repo", 1)