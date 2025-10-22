"""
Tests for git_utils module
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
from github_events_monitor.utils.git_utils import (
    run_git_command, check_git_repo, git_remote_exists, ensure_remote,
    fetch_all, fetch_pr_branch, branch_exists, create_work_branch_from,
    merge_branch, in_merge_or_rebase, staged_or_uncommitted,
    finish_merge_or_rebase_after_agent, compute_merge_base,
    get_current_branch, checkout_branch, push_branch, squash_commits_since,
    rebase_onto
)


class TestGitUtils:
    """Test cases for git utilities."""
    
    @patch('subprocess.run')
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = run_git_command("git status", capture=True)
        
        mock_run.assert_called_once()
        assert result == mock_result
    
    @patch('subprocess.run')
    def test_run_git_command_failure(self, mock_run):
        """Test git command execution failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        
        with pytest.raises(subprocess.CalledProcessError):
            run_git_command("git invalid-command")
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_check_git_repo_success(self, mock_run_git):
        """Test successful git repo check."""
        mock_run_git.return_value = MagicMock()
        
        # Should not raise exception
        check_git_repo()
        mock_run_git.assert_called_once_with("git rev-parse --is-inside-work-tree", capture=False)
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_check_git_repo_failure(self, mock_run_git):
        """Test git repo check failure."""
        mock_run_git.side_effect = subprocess.CalledProcessError(1, "git")
        
        with pytest.raises(SystemExit):
            check_git_repo()
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_git_remote_exists_true(self, mock_run_git):
        """Test remote exists check when remote exists."""
        mock_run_git.return_value = MagicMock()
        
        result = git_remote_exists("origin")
        
        assert result is True
        mock_run_git.assert_called_once()
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_git_remote_exists_false(self, mock_run_git):
        """Test remote exists check when remote doesn't exist."""
        mock_run_git.side_effect = subprocess.CalledProcessError(1, "git")
        
        result = git_remote_exists("nonexistent")
        
        assert result is False
    
    @patch('github_events_monitor.utils.git_utils.git_remote_exists')
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_ensure_remote_new(self, mock_run_git, mock_remote_exists):
        """Test ensuring remote when it doesn't exist."""
        mock_remote_exists.return_value = False
        
        ensure_remote("upstream", "https://github.com/owner/repo.git")
        
        mock_run_git.assert_called_once()
    
    @patch('github_events_monitor.utils.git_utils.git_remote_exists')
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_ensure_remote_exists(self, mock_run_git, mock_remote_exists):
        """Test ensuring remote when it already exists."""
        mock_remote_exists.return_value = True
        
        ensure_remote("upstream", "https://github.com/owner/repo.git")
        
        mock_run_git.assert_not_called()
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_fetch_all(self, mock_run_git):
        """Test fetching all remotes."""
        fetch_all("upstream", "origin")
        
        assert mock_run_git.call_count == 2
        calls = mock_run_git.call_args_list
        assert "upstream" in calls[0][0][0]
        assert "origin" in calls[1][0][0]
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_fetch_pr_branch_success(self, mock_run_git):
        """Test successful PR branch fetch."""
        mock_run_git.return_value = MagicMock()
        
        result = fetch_pr_branch("upstream", 123)
        
        assert result == "refs/heads/pr/123"
        mock_run_git.assert_called_once()
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_fetch_pr_branch_with_fallback(self, mock_run_git):
        """Test PR branch fetch with fallback remote."""
        # First call fails, second succeeds
        mock_run_git.side_effect = [
            subprocess.CalledProcessError(1, "git"),
            MagicMock()
        ]
        
        result = fetch_pr_branch("upstream", 123, "origin")
        
        assert result == "refs/heads/pr/123"
        assert mock_run_git.call_count == 2
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_branch_exists_true(self, mock_run_git):
        """Test branch exists when branch exists."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run_git.return_value = mock_result
        
        result = branch_exists("main")
        
        assert result is True
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_branch_exists_false(self, mock_run_git):
        """Test branch exists when branch doesn't exist."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run_git.return_value = mock_result
        
        result = branch_exists("nonexistent")
        
        assert result is False
    
    @patch('github_events_monitor.utils.git_utils.branch_exists')
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_create_work_branch_from_with_force(self, mock_run_git, mock_branch_exists):
        """Test creating work branch with force delete."""
        mock_branch_exists.return_value = True
        
        create_work_branch_from("refs/heads/pr/123", "work-branch", force=True)
        
        assert mock_run_git.call_count == 2
        calls = mock_run_git.call_args_list
        assert "branch -D" in calls[0][0][0]
        assert "checkout -b" in calls[1][0][0]
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_merge_branch_success(self, mock_run_git):
        """Test successful branch merge."""
        mock_run_git.return_value = MagicMock()
        
        merge_branch("feature-branch")
        
        mock_run_git.assert_called_once()
        call_args = mock_run_git.call_args[0][0]
        assert "merge" in call_args
        assert "feature-branch" in call_args
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_merge_branch_conflict(self, mock_run_git):
        """Test branch merge with conflicts."""
        mock_run_git.side_effect = subprocess.CalledProcessError(1, "git")
        
        with pytest.raises(subprocess.CalledProcessError):
            merge_branch("feature-branch")
    
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_in_merge_or_rebase_merge(self, mock_isdir, mock_exists):
        """Test merge state detection."""
        mock_exists.return_value = True
        mock_isdir.return_value = False
        
        in_state, state = in_merge_or_rebase()
        
        assert in_state is True
        assert state == "merge"
    
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_in_merge_or_rebase_rebase(self, mock_isdir, mock_exists):
        """Test rebase state detection."""
        mock_exists.return_value = False
        mock_isdir.return_value = True
        
        in_state, state = in_merge_or_rebase()
        
        assert in_state is True
        assert state == "rebase"
    
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_in_merge_or_rebase_none(self, mock_isdir, mock_exists):
        """Test no merge/rebase state."""
        mock_exists.return_value = False
        mock_isdir.return_value = False
        
        in_state, state = in_merge_or_rebase()
        
        assert in_state is False
        assert state == ""
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_staged_or_uncommitted_true(self, mock_run_git):
        """Test staged or uncommitted changes detection."""
        mock_result = MagicMock()
        mock_result.stdout = "M  file.txt"
        mock_run_git.return_value = mock_result
        
        result = staged_or_uncommitted()
        
        assert result is True
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_staged_or_uncommitted_false(self, mock_run_git):
        """Test no staged or uncommitted changes."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_run_git.return_value = mock_result
        
        result = staged_or_uncommitted()
        
        assert result is False
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_compute_merge_base(self, mock_run_git):
        """Test merge base computation."""
        mock_result = MagicMock()
        mock_result.stdout = "abc123def456"
        mock_run_git.return_value = mock_result
        
        result = compute_merge_base("main", "feature")
        
        assert result == "abc123def456"
        mock_run_git.assert_called_once()
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_get_current_branch(self, mock_run_git):
        """Test getting current branch."""
        mock_result = MagicMock()
        mock_result.stdout = "feature-branch"
        mock_run_git.return_value = mock_result
        
        result = get_current_branch()
        
        assert result == "feature-branch"
        mock_run_git.assert_called_once()
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_checkout_branch(self, mock_run_git):
        """Test checking out a branch."""
        checkout_branch("feature-branch")
        
        mock_run_git.assert_called_once()
        call_args = mock_run_git.call_args[0][0]
        assert "checkout" in call_args
        assert "feature-branch" in call_args
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_checkout_branch_create(self, mock_run_git):
        """Test creating and checking out a branch."""
        checkout_branch("feature-branch", create=True)
        
        mock_run_git.assert_called_once()
        call_args = mock_run_git.call_args[0][0]
        assert "checkout -b" in call_args
        assert "feature-branch" in call_args
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_push_branch(self, mock_run_git):
        """Test pushing a branch."""
        push_branch("origin", "feature-branch")
        
        mock_run_git.assert_called_once()
        call_args = mock_run_git.call_args[0][0]
        assert "push" in call_args
        assert "origin" in call_args
        assert "feature-branch" in call_args
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_push_branch_force_upstream(self, mock_run_git):
        """Test force pushing with upstream."""
        push_branch("origin", "feature-branch", force=True, set_upstream=True)
        
        mock_run_git.assert_called_once()
        call_args = mock_run_git.call_args[0][0]
        assert "push" in call_args
        assert "--force" in call_args
        assert "-u" in call_args
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_squash_commits_since(self, mock_run_git):
        """Test squashing commits."""
        squash_commits_since("abc123", "Squashed commits")
        
        assert mock_run_git.call_count == 2
        calls = mock_run_git.call_args_list
        assert "reset --soft" in calls[0][0][0]
        assert "commit" in calls[1][0][0]
    
    @patch('github_events_monitor.utils.git_utils.run_git_command')
    def test_rebase_onto(self, mock_run_git):
        """Test rebasing onto a branch."""
        rebase_onto("main", "feature")
        
        mock_run_git.assert_called_once()
        call_args = mock_run_git.call_args[0][0]
        assert "rebase" in call_args
        assert "main" in call_args
        assert "feature" in call_args