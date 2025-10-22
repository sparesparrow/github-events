"""
Merge Utilities Module

Provides reusable functions for merge and rebase operations, conflict resolution,
and automated PR management workflows.
Designed to be consistent with the existing codebase patterns.
"""

import os
import sys
from typing import List, Optional, Dict, Any, Tuple
from .git_utils import (
    run_git_command, check_git_repo, ensure_remote, fetch_all, 
    fetch_pr_branch, create_work_branch_from, merge_branch,
    in_merge_or_rebase, finish_merge_or_rebase_after_agent,
    compute_merge_base, get_current_branch, checkout_branch,
    push_branch, squash_commits_since, rebase_onto
)
from .github_utils import (
    list_open_prs, create_github_pr, create_pr_with_gh_cli,
    get_current_user_login_from_token, parse_repository_url,
    get_default_branch, is_gh_cli_available
)
from .shell_utils import run_command, is_command_available


class MergeAndSquashConfig:
    """Configuration class for merge and squash operations."""
    
    def __init__(
        self,
        upstream_remote: str = "upstream",
        origin_remote: str = "origin", 
        upstream_url: Optional[str] = None,
        cursor_cmd_fix: str = 'cursor-agent -f agent "fix conflicts and complete merge/rebase"',
        cursor_cmd_ack: str = 'cursor-agent -f agent "use ack tool to test and fix all workflows"',
        github_token: Optional[str] = None,
        dry_run: bool = False
    ):
        self.upstream_remote = upstream_remote
        self.origin_remote = origin_remote
        self.upstream_url = upstream_url
        self.cursor_cmd_fix = cursor_cmd_fix
        self.cursor_cmd_ack = cursor_cmd_ack
        self.github_token = github_token
        self.dry_run = dry_run


class MergeAndSquashWorkflow:
    """Main workflow class for merge and squash operations."""
    
    def __init__(self, config: MergeAndSquashConfig):
        self.config = config
        self.work_branch = f"merge-work-{int(os.urandom(4).hex(), 16)}"
    
    def run_cursor_agent(self, cmd: str) -> None:
        """Run cursor agent command with dry-run support."""
        if self.config.dry_run:
            print(f"[dry-run] would run: {cmd}")
            return
        print(f"Running cursor agent command: {cmd}")
        run_command(cmd)
    
    def setup_remotes(self, upstream_url: str) -> None:
        """Set up git remotes."""
        check_git_repo()
        ensure_remote(self.config.upstream_remote, upstream_url)
        fetch_all(self.config.upstream_remote, self.config.origin_remote)
    
    def fetch_and_prepare_pr(self, pr_number: int) -> str:
        """Fetch PR branch and prepare for merging."""
        local_pr_ref = fetch_pr_branch(
            self.config.upstream_remote, 
            pr_number, 
            self.config.origin_remote
        )
        create_work_branch_from(local_pr_ref, self.work_branch)
        return local_pr_ref
    
    def merge_additional_prs(self, pr_numbers: List[int]) -> None:
        """Merge additional PRs into the work branch."""
        for pr_num in pr_numbers:
            try:
                local_pr_ref = fetch_pr_branch(
                    self.config.upstream_remote, 
                    pr_num, 
                    self.config.origin_remote
                )
                merge_branch(local_pr_ref, self.config.dry_run)
                print(f"Successfully merged PR #{pr_num}")
            except Exception as e:
                print(f"Failed to merge PR #{pr_num}: {e}")
                if not self.config.dry_run:
                    self.run_cursor_agent(self.config.cursor_cmd_fix)
                    finish_merge_or_rebase_after_agent(self.config.dry_run)
    
    def squash_and_rebase(self, upstream_master: str) -> None:
        """Squash commits and rebase onto upstream master."""
        merge_base = compute_merge_base(upstream_master, self.work_branch)
        squash_commits_since(merge_base, "Merged and squashed PRs")
        
        if not self.config.dry_run:
            try:
                rebase_onto(upstream_master, self.work_branch)
            except Exception as e:
                print(f"Rebase failed: {e}")
                self.run_cursor_agent(self.config.cursor_cmd_fix)
                finish_merge_or_rebase_after_agent(self.config.dry_run)
    
    def push_and_create_pr(self, owner: str, repo: str, base_branch: str, title: str, body: str = "") -> Optional[Dict[str, Any]]:
        """Push branch and create PR."""
        if self.config.dry_run:
            print(f"[dry-run] would push {self.work_branch} and create PR")
            return None
        
        # Push branch
        push_branch(self.config.origin_remote, self.work_branch, force=True, set_upstream=True)
        
        # Create PR
        if is_gh_cli_available():
            return create_pr_with_gh_cli(
                self.config.origin_remote, 
                self.work_branch, 
                base_branch, 
                title, 
                body
            )
        elif self.config.github_token:
            # Get current user for head ref
            username = get_current_user_login_from_token(self.config.github_token)
            if username:
                head_ref = f"{username}:{self.work_branch}"
            else:
                head_ref = self.work_branch
            
            return create_github_pr(
                owner, repo, head_ref, base_branch, title, body, self.config.github_token
            )
        else:
            print("No GitHub CLI or token available for PR creation")
            return None
    
    def cleanup(self) -> None:
        """Clean up work branch."""
        if not self.config.dry_run:
            try:
                run_git_command(f"git checkout main")
                run_git_command(f"git branch -D {self.work_branch}")
            except Exception as e:
                print(f"Cleanup warning: {e}")


def interactive_pr_selection(owner: str, repo: str, token: Optional[str] = None) -> List[int]:
    """
    Interactively select PRs from open PRs list.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub API token
        
    Returns:
        List of selected PR numbers
    """
    try:
        prs = list_open_prs(owner, repo, token)
        if not prs:
            print("No open PRs found")
            return []
        
        print("\nOpen PRs:")
        for i, pr in enumerate(prs, 1):
            print(f"{i}. #{pr['number']}: {pr['title']} (by {pr['user']['login']})")
        
        print("\nEnter PR numbers to include (comma-separated, or 'all' for all):")
        selection = input().strip()
        
        if selection.lower() == 'all':
            return [pr['number'] for pr in prs]
        
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            return [prs[i]['number'] for i in indices if 0 <= i < len(prs)]
        except (ValueError, IndexError):
            print("Invalid selection")
            return []
    
    except Exception as e:
        print(f"Error fetching PRs: {e}")
        return []


def run_merge_and_squash_workflow(
    primary_pr: int,
    additional_prs: Optional[List[int]] = None,
    upstream_url: Optional[str] = None,
    config: Optional[MergeAndSquashConfig] = None
) -> Optional[Dict[str, Any]]:
    """
    Run the complete merge and squash workflow.
    
    Args:
        primary_pr: Primary PR number to start with
        additional_prs: Additional PR numbers to merge
        upstream_url: Upstream repository URL
        config: Configuration object
        
    Returns:
        Created PR information if successful, None otherwise
    """
    if config is None:
        config = MergeAndSquashConfig()
    
    if upstream_url is None:
        upstream_url = os.getenv("UPSTREAM_URL", "git@github.com:sparesparrow/openssl-tools.git")
    
    # Parse repository info
    try:
        owner, repo = parse_repository_url(upstream_url)
    except ValueError as e:
        print(f"Error parsing repository URL: {e}")
        return None
    
    workflow = MergeAndSquashWorkflow(config)
    
    try:
        # Setup
        workflow.setup_remotes(upstream_url)
        
        # Fetch primary PR
        workflow.fetch_and_prepare_pr(primary_pr)
        
        # Merge additional PRs
        if additional_prs:
            workflow.merge_additional_prs(additional_prs)
        
        # Get base branch
        base_branch = get_default_branch(owner, repo, config.github_token)
        upstream_master = f"{config.upstream_remote}/{base_branch}"
        
        # Squash and rebase
        workflow.squash_and_rebase(upstream_master)
        
        # Create PR
        title = f"Merged PRs: #{primary_pr}" + (f" + {len(additional_prs)} others" if additional_prs else "")
        body = f"Automated merge of PR #{primary_pr}" + (f" and {len(additional_prs)} additional PRs" if additional_prs else "")
        
        pr_info = workflow.push_and_create_pr(owner, repo, base_branch, title, body)
        
        if pr_info:
            print(f"Created PR: {pr_info.get('url', 'Unknown URL')}")
        
        return pr_info
    
    except Exception as e:
        print(f"Workflow failed: {e}")
        return None
    
    finally:
        workflow.cleanup()


def validate_environment() -> bool:
    """
    Validate that required tools and environment are available.
    
    Returns:
        True if environment is valid, False otherwise
    """
    # Check git
    if not is_command_available("git"):
        print("ERROR: git is not available")
        return False
    
    # Check cursor-agent
    if not is_command_available("cursor-agent"):
        print("WARNING: cursor-agent is not available")
    
    # Check GitHub CLI or requests
    if not is_gh_cli_available() and not is_command_available("python3 -c 'import requests'"):
        print("WARNING: Neither GitHub CLI nor requests library available for PR operations")
    
    return True