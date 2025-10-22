"""
Tests for merge_utils module
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from github_events_monitor.utils.merge_utils import (
    MergeAndSquashConfig, MergeAndSquashWorkflow,
    interactive_pr_selection, run_merge_and_squash_workflow,
    validate_environment
)


class TestMergeAndSquashConfig:
    """Test cases for MergeAndSquashConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MergeAndSquashConfig()
        
        assert config.upstream_remote == "upstream"
        assert config.origin_remote == "origin"
        assert config.upstream_url is None
        assert "cursor-agent" in config.cursor_cmd_fix
        assert "cursor-agent" in config.cursor_cmd_ack
        assert config.github_token is None
        assert config.dry_run is False
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = MergeAndSquashConfig(
            upstream_remote="custom_upstream",
            origin_remote="custom_origin",
            upstream_url="https://github.com/owner/repo.git",
            cursor_cmd_fix="custom fix command",
            cursor_cmd_ack="custom ack command",
            github_token="test_token",
            dry_run=True
        )
        
        assert config.upstream_remote == "custom_upstream"
        assert config.origin_remote == "custom_origin"
        assert config.upstream_url == "https://github.com/owner/repo.git"
        assert config.cursor_cmd_fix == "custom fix command"
        assert config.cursor_cmd_ack == "custom ack command"
        assert config.github_token == "test_token"
        assert config.dry_run is True


class TestMergeAndSquashWorkflow:
    """Test cases for MergeAndSquashWorkflow."""
    
    def test_init(self):
        """Test workflow initialization."""
        config = MergeAndSquashConfig()
        workflow = MergeAndSquashWorkflow(config)
        
        assert workflow.config == config
        assert workflow.work_branch.startswith("merge-work-")
    
    @patch('github_events_monitor.utils.merge_utils.run_command')
    def test_run_cursor_agent_dry_run(self, mock_run_command):
        """Test cursor agent execution in dry run mode."""
        config = MergeAndSquashConfig(dry_run=True)
        workflow = MergeAndSquashWorkflow(config)
        
        workflow.run_cursor_agent("test command")
        
        mock_run_command.assert_not_called()
    
    @patch('github_events_monitor.utils.merge_utils.run_command')
    def test_run_cursor_agent_normal(self, mock_run_command):
        """Test cursor agent execution in normal mode."""
        config = MergeAndSquashConfig(dry_run=False)
        workflow = MergeAndSquashWorkflow(config)
        
        workflow.run_cursor_agent("test command")
        
        mock_run_command.assert_called_once_with("test command")
    
    @patch('github_events_monitor.utils.merge_utils.check_git_repo')
    @patch('github_events_monitor.utils.merge_utils.ensure_remote')
    @patch('github_events_monitor.utils.merge_utils.fetch_all')
    def test_setup_remotes(self, mock_fetch_all, mock_ensure_remote, mock_check_git_repo):
        """Test remote setup."""
        config = MergeAndSquashConfig()
        workflow = MergeAndSquashWorkflow(config)
        
        workflow.setup_remotes("https://github.com/owner/repo.git")
        
        mock_check_git_repo.assert_called_once()
        mock_ensure_remote.assert_called_once_with("upstream", "https://github.com/owner/repo.git")
        mock_fetch_all.assert_called_once_with("upstream", "origin")
    
    @patch('github_events_monitor.utils.merge_utils.fetch_pr_branch')
    @patch('github_events_monitor.utils.merge_utils.create_work_branch_from')
    def test_fetch_and_prepare_pr(self, mock_create_branch, mock_fetch_pr):
        """Test PR fetching and preparation."""
        config = MergeAndSquashConfig()
        workflow = MergeAndSquashWorkflow(config)
        mock_fetch_pr.return_value = "refs/heads/pr/123"
        
        result = workflow.fetch_and_prepare_pr(123)
        
        assert result == "refs/heads/pr/123"
        mock_fetch_pr.assert_called_once_with("upstream", 123, "origin")
        mock_create_branch.assert_called_once_with("refs/heads/pr/123", workflow.work_branch)
    
    @patch('github_events_monitor.utils.merge_utils.fetch_pr_branch')
    @patch('github_events_monitor.utils.merge_utils.merge_branch')
    def test_merge_additional_prs_success(self, mock_merge, mock_fetch_pr):
        """Test successful additional PR merging."""
        config = MergeAndSquashConfig()
        workflow = MergeAndSquashWorkflow(config)
        mock_fetch_pr.return_value = "refs/heads/pr/124"
        mock_merge.return_value = None
        
        workflow.merge_additional_prs([124, 125])
        
        assert mock_fetch_pr.call_count == 2
        assert mock_merge.call_count == 2
    
    @patch('github_events_monitor.utils.merge_utils.fetch_pr_branch')
    @patch('github_events_monitor.utils.merge_utils.merge_branch')
    @patch('github_events_monitor.utils.merge_utils.run_command')
    @patch('github_events_monitor.utils.merge_utils.finish_merge_or_rebase_after_agent')
    def test_merge_additional_prs_conflict(self, mock_finish, mock_run_command, mock_merge, mock_fetch_pr):
        """Test additional PR merging with conflicts."""
        config = MergeAndSquashConfig(dry_run=False)
        workflow = MergeAndSquashWorkflow(config)
        mock_fetch_pr.return_value = "refs/heads/pr/124"
        mock_merge.side_effect = Exception("Merge conflict")
        
        workflow.merge_additional_prs([124])
        
        mock_run_command.assert_called_once()
        mock_finish.assert_called_once()
    
    @patch('github_events_monitor.utils.merge_utils.compute_merge_base')
    @patch('github_events_monitor.utils.merge_utils.squash_commits_since')
    @patch('github_events_monitor.utils.merge_utils.rebase_onto')
    def test_squash_and_rebase_success(self, mock_rebase, mock_squash, mock_merge_base):
        """Test successful squash and rebase."""
        config = MergeAndSquashConfig(dry_run=False)
        workflow = MergeAndSquashWorkflow(config)
        mock_merge_base.return_value = "abc123"
        
        workflow.squash_and_rebase("upstream/main")
        
        mock_merge_base.assert_called_once_with("upstream/main", workflow.work_branch)
        mock_squash.assert_called_once_with("abc123", "Merged and squashed PRs")
        mock_rebase.assert_called_once_with("upstream/main", workflow.work_branch)
    
    @patch('github_events_monitor.utils.merge_utils.compute_merge_base')
    @patch('github_events_monitor.utils.merge_utils.squash_commits_since')
    @patch('github_events_monitor.utils.merge_utils.rebase_onto')
    @patch('github_events_monitor.utils.merge_utils.run_command')
    @patch('github_events_monitor.utils.merge_utils.finish_merge_or_rebase_after_agent')
    def test_squash_and_rebase_conflict(self, mock_finish, mock_run_command, mock_rebase, mock_squash, mock_merge_base):
        """Test squash and rebase with conflicts."""
        config = MergeAndSquashConfig(dry_run=False)
        workflow = MergeAndSquashWorkflow(config)
        mock_merge_base.return_value = "abc123"
        mock_rebase.side_effect = Exception("Rebase conflict")
        
        workflow.squash_and_rebase("upstream/main")
        
        mock_run_command.assert_called_once()
        mock_finish.assert_called_once()
    
    @patch('github_events_monitor.utils.merge_utils.push_branch')
    @patch('github_events_monitor.utils.merge_utils.create_pr_with_gh_cli')
    @patch('github_events_monitor.utils.merge_utils.is_gh_cli_available')
    def test_push_and_create_pr_gh_cli(self, mock_gh_available, mock_create_pr, mock_push):
        """Test push and PR creation with gh CLI."""
        config = MergeAndSquashConfig(dry_run=False)
        workflow = MergeAndSquashWorkflow(config)
        mock_gh_available.return_value = True
        mock_create_pr.return_value = {"url": "https://github.com/owner/repo/pull/1"}
        
        result = workflow.push_and_create_pr("owner", "repo", "main", "Test PR", "Body")
        
        assert result["url"] == "https://github.com/owner/repo/pull/1"
        mock_push.assert_called_once_with("origin", workflow.work_branch, force=True, set_upstream=True)
        mock_create_pr.assert_called_once()
    
    @patch('github_events_monitor.utils.merge_utils.push_branch')
    @patch('github_events_monitor.utils.merge_utils.create_github_pr')
    @patch('github_events_monitor.utils.merge_utils.is_gh_cli_available')
    @patch('github_events_monitor.utils.merge_utils.get_current_user_login_from_token')
    def test_push_and_create_pr_api(self, mock_get_user, mock_create_pr, mock_gh_available, mock_push):
        """Test push and PR creation with GitHub API."""
        config = MergeAndSquashConfig(dry_run=False, github_token="test_token")
        workflow = MergeAndSquashWorkflow(config)
        mock_gh_available.return_value = False
        mock_get_user.return_value = "testuser"
        mock_create_pr.return_value = {"url": "https://github.com/owner/repo/pull/1"}
        
        result = workflow.push_and_create_pr("owner", "repo", "main", "Test PR", "Body")
        
        assert result["url"] == "https://github.com/owner/repo/pull/1"
        mock_push.assert_called_once()
        mock_create_pr.assert_called_once_with("owner", "repo", "testuser:merge-work-123", "main", "Test PR", "Body", "test_token")
    
    @patch('github_events_monitor.utils.merge_utils.run_git_command')
    def test_cleanup(self, mock_run_git):
        """Test workflow cleanup."""
        config = MergeAndSquashConfig(dry_run=False)
        workflow = MergeAndSquashWorkflow(config)
        
        workflow.cleanup()
        
        assert mock_run_git.call_count == 2
        calls = mock_run_git.call_args_list
        assert "checkout main" in calls[0][0][0]
        assert f"branch -D {workflow.work_branch}" in calls[1][0][0]


class TestInteractivePRSelection:
    """Test cases for interactive PR selection."""
    
    @patch('github_events_monitor.utils.merge_utils.list_open_prs')
    @patch('builtins.input')
    def test_interactive_selection_specific(self, mock_input, mock_list_prs):
        """Test interactive PR selection with specific numbers."""
        mock_list_prs.return_value = [
            {"number": 1, "title": "PR 1", "user": {"login": "user1"}},
            {"number": 2, "title": "PR 2", "user": {"login": "user2"}}
        ]
        mock_input.return_value = "1,2"
        
        result = interactive_pr_selection("owner", "repo", "token")
        
        assert result == [1, 2]
        mock_list_prs.assert_called_once_with("owner", "repo", "token")
    
    @patch('github_events_monitor.utils.merge_utils.list_open_prs')
    @patch('builtins.input')
    def test_interactive_selection_all(self, mock_input, mock_list_prs):
        """Test interactive PR selection with 'all'."""
        mock_list_prs.return_value = [
            {"number": 1, "title": "PR 1", "user": {"login": "user1"}},
            {"number": 2, "title": "PR 2", "user": {"login": "user2"}}
        ]
        mock_input.return_value = "all"
        
        result = interactive_pr_selection("owner", "repo", "token")
        
        assert result == [1, 2]
    
    @patch('github_events_monitor.utils.merge_utils.list_open_prs')
    def test_interactive_selection_no_prs(self, mock_list_prs):
        """Test interactive PR selection with no PRs."""
        mock_list_prs.return_value = []
        
        result = interactive_pr_selection("owner", "repo", "token")
        
        assert result == []
    
    @patch('github_events_monitor.utils.merge_utils.list_open_prs')
    @patch('builtins.input')
    def test_interactive_selection_invalid(self, mock_input, mock_list_prs):
        """Test interactive PR selection with invalid input."""
        mock_list_prs.return_value = [
            {"number": 1, "title": "PR 1", "user": {"login": "user1"}}
        ]
        mock_input.return_value = "invalid"
        
        result = interactive_pr_selection("owner", "repo", "token")
        
        assert result == []
    
    @patch('github_events_monitor.utils.merge_utils.list_open_prs')
    def test_interactive_selection_error(self, mock_list_prs):
        """Test interactive PR selection with API error."""
        mock_list_prs.side_effect = Exception("API error")
        
        result = interactive_pr_selection("owner", "repo", "token")
        
        assert result == []


class TestRunMergeAndSquashWorkflow:
    """Test cases for run_merge_and_squash_workflow."""
    
    @patch('github_events_monitor.utils.merge_utils.parse_repository_url')
    @patch('github_events_monitor.utils.merge_utils.MergeAndSquashWorkflow')
    def test_run_workflow_success(self, mock_workflow_class, mock_parse_url):
        """Test successful workflow execution."""
        mock_parse_url.return_value = ("owner", "repo")
        mock_workflow = MagicMock()
        mock_workflow.push_and_create_pr.return_value = {"url": "https://github.com/owner/repo/pull/1"}
        mock_workflow_class.return_value = mock_workflow
        
        result = run_merge_and_squash_workflow(123, [124, 125])
        
        assert result["url"] == "https://github.com/owner/repo/pull/1"
        mock_workflow.setup_remotes.assert_called_once()
        mock_workflow.fetch_and_prepare_pr.assert_called_once_with(123)
        mock_workflow.merge_additional_prs.assert_called_once_with([124, 125])
        mock_workflow.squash_and_rebase.assert_called_once()
        mock_workflow.push_and_create_pr.assert_called_once()
        mock_workflow.cleanup.assert_called_once()
    
    @patch('github_events_monitor.utils.merge_utils.parse_repository_url')
    def test_run_workflow_invalid_url(self, mock_parse_url):
        """Test workflow execution with invalid URL."""
        mock_parse_url.side_effect = ValueError("Invalid URL")
        
        result = run_merge_and_squash_workflow(123)
        
        assert result is None
    
    @patch('github_events_monitor.utils.merge_utils.parse_repository_url')
    @patch('github_events_monitor.utils.merge_utils.MergeAndSquashWorkflow')
    def test_run_workflow_failure(self, mock_workflow_class, mock_parse_url):
        """Test workflow execution failure."""
        mock_parse_url.return_value = ("owner", "repo")
        mock_workflow = MagicMock()
        mock_workflow.setup_remotes.side_effect = Exception("Setup failed")
        mock_workflow_class.return_value = mock_workflow
        
        result = run_merge_and_squash_workflow(123)
        
        assert result is None
        mock_workflow.cleanup.assert_called_once()


class TestValidateEnvironment:
    """Test cases for environment validation."""
    
    @patch('github_events_monitor.utils.merge_utils.is_command_available')
    def test_validate_environment_success(self, mock_is_available):
        """Test successful environment validation."""
        mock_is_available.return_value = True
        
        result = validate_environment()
        
        assert result is True
        # Should check git and cursor-agent
        assert mock_is_available.call_count >= 2
    
    @patch('github_events_monitor.utils.merge_utils.is_command_available')
    def test_validate_environment_no_git(self, mock_is_available):
        """Test environment validation without git."""
        def side_effect(cmd):
            return cmd == "git"
        mock_is_available.side_effect = side_effect
        
        result = validate_environment()
        
        assert result is False
    
    @patch('github_events_monitor.utils.merge_utils.is_command_available')
    def test_validate_environment_no_cursor_agent(self, mock_is_available):
        """Test environment validation without cursor-agent (warning only)."""
        def side_effect(cmd):
            return cmd != "cursor-agent"
        mock_is_available.side_effect = side_effect
        
        result = validate_environment()
        
        # Should still pass even without cursor-agent
        assert result is True