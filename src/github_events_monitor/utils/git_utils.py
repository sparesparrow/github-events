"""
Git Utilities Module

Provides reusable functions for git operations, branch management, and conflict resolution.
Designed to be consistent with the existing codebase patterns.
"""

import os
import shlex
import subprocess
import sys
from typing import List, Optional, Tuple


def run_git_command(cmd: str, cwd: Optional[str] = None, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """
    Run a git command (string). Raises on non-zero when check True.
    
    Args:
        cmd: Git command to execute
        cwd: Working directory for the command
        check: Whether to raise exception on non-zero exit code
        capture: Whether to capture stdout/stderr
        
    Returns:
        CompletedProcess object with command results
    """
    print(f"+ {cmd}")
    if capture:
        return subprocess.run(cmd, cwd=cwd, shell=True, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    else:
        return subprocess.run(cmd, cwd=cwd, shell=True, check=check)


def check_git_repo() -> None:
    """Verify that we're running from inside a git repository."""
    try:
        run_git_command("git rev-parse --is-inside-work-tree", capture=False)
    except subprocess.CalledProcessError:
        print("ERROR: This script must be run from inside a git repository clone.", file=sys.stderr)
        sys.exit(2)


def git_remote_exists(name: str) -> bool:
    """
    Check if a git remote exists.
    
    Args:
        name: Remote name to check
        
    Returns:
        True if remote exists, False otherwise
    """
    try:
        run_git_command(f"git remote get-url {shlex.quote(name)}", capture=True)
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_remote(name: str, url: str) -> None:
    """
    Ensure a git remote exists, creating it if necessary.
    
    Args:
        name: Remote name
        url: Remote URL
    """
    if not git_remote_exists(name):
        print(f"Adding remote {name} -> {url}")
        run_git_command(f"git remote add {shlex.quote(name)} {shlex.quote(url)}")


def fetch_all(upstream: str, origin: str) -> None:
    """
    Fetch all branches and tags from upstream and origin remotes.
    
    Args:
        upstream: Upstream remote name
        origin: Origin remote name
    """
    run_git_command(f"git fetch {shlex.quote(upstream)} --prune --tags")
    run_git_command(f"git fetch {shlex.quote(origin)} --prune --tags")


def fetch_pr_branch(upstream: str, pr_num: int, fallback_remote: Optional[str] = None) -> str:
    """
    Fetch pull/<pr_num>/head into refs/heads/pr/<pr_num>.
    
    Args:
        upstream: Upstream remote name
        pr_num: Pull request number
        fallback_remote: Optional fallback remote if upstream fails
        
    Returns:
        Local branch ref name: refs/heads/pr/<pr_num>
    """
    local_branch = f"refs/heads/pr/{pr_num}"
    try:
        run_git_command(f"git fetch {shlex.quote(upstream)} pull/{pr_num}/head:{local_branch}")
    except subprocess.CalledProcessError:
        if fallback_remote:
            run_git_command(f"git fetch {shlex.quote(fallback_remote)} pull/{pr_num}/head:{local_branch}")
        else:
            raise
    return local_branch


def branch_exists(name: str) -> bool:
    """
    Check if a local branch exists.
    
    Args:
        name: Branch name to check
        
    Returns:
        True if branch exists, False otherwise
    """
    cp = run_git_command(f"git show-ref --verify --quiet refs/heads/{shlex.quote(name)}", check=False, capture=False)
    return cp.returncode == 0


def create_work_branch_from(local_pr_ref: str, work_branch: str, force: bool = True) -> None:
    """
    Create a work branch from a local PR reference.
    
    Args:
        local_pr_ref: Local PR reference to branch from
        work_branch: Name of work branch to create
        force: Whether to force delete existing branch
    """
    if force and branch_exists(work_branch):
        run_git_command(f"git branch -D {shlex.quote(work_branch)}")
    run_git_command(f"git checkout -b {shlex.quote(work_branch)} {shlex.quote(local_pr_ref)}")


def merge_branch(local_branch: str, dry_run: bool = False) -> None:
    """
    Attempt to merge a branch with no fast-forward.
    
    Args:
        local_branch: Branch to merge
        dry_run: If True, only print what would be done
        
    Raises:
        subprocess.CalledProcessError: If merge fails (likely due to conflicts)
    """
    cmd = f"git merge --no-ff --no-edit {shlex.quote(local_branch)}"
    if dry_run:
        print("[dry-run] would run:", cmd)
        return
    try:
        run_git_command(cmd)
        print(f"Merge of {local_branch} succeeded.")
    except subprocess.CalledProcessError:
        print(f"Merge of {local_branch} returned non-zero (likely conflicts).")
        raise


def in_merge_or_rebase() -> Tuple[bool, str]:
    """
    Check if we're currently in a merge or rebase state.
    
    Returns:
        Tuple of (is_in_state, state_name) where state_name is "merge" or "rebase"
    """
    if os.path.exists(".git/MERGE_HEAD"):
        return True, "merge"
    if os.path.isdir(".git/rebase-apply") or os.path.isdir(".git/rebase-merge"):
        return True, "rebase"
    return False, ""


def staged_or_uncommitted() -> bool:
    """
    Check if there are staged or uncommitted changes.
    
    Returns:
        True if there are staged or uncommitted changes
    """
    cp = run_git_command("git status --porcelain", capture=True)
    return bool(cp.stdout.strip())


def finish_merge_or_rebase_after_agent(dry_run: bool = False) -> None:
    """
    Complete merge or rebase after agent has resolved conflicts.
    
    Args:
        dry_run: If True, only print what would be done
    """
    in_state, state = in_merge_or_rebase()
    if in_state:
        print(f"Detected {state} in progress; attempting to finalize.")
        if state == "merge":
            # stage everything and commit
            run_git_command("git add -A")
            try:
                run_git_command('git commit --no-edit')
            except subprocess.CalledProcessError:
                run_git_command('git commit -m "Merge conflicts resolved by cursor-agent"')
        else:
            # rebase
            try:
                run_git_command("git rebase --continue")
            except subprocess.CalledProcessError:
                run_git_command("git add -A")
                run_git_command("git rebase --continue")
    else:
        # Not in a merge/rebase; maybe agent created staged changes -> commit them
        if staged_or_uncommitted():
            run_git_command("git add -A")
            run_git_command('git commit -m "Conflict resolution edits by cursor-agent"')


def compute_merge_base(upstream_master: str, branch: str) -> str:
    """
    Compute the merge base between upstream master and a branch.
    
    Args:
        upstream_master: Upstream master branch reference
        branch: Branch reference
        
    Returns:
        Commit hash of the merge base
    """
    cp = run_git_command(f"git merge-base {shlex.quote(upstream_master)} {shlex.quote(branch)}", capture=True)
    return cp.stdout.strip()


def get_current_branch() -> str:
    """
    Get the current branch name.
    
    Returns:
        Current branch name
    """
    cp = run_git_command("git rev-parse --abbrev-ref HEAD", capture=True)
    return cp.stdout.strip()


def checkout_branch(branch: str, create: bool = False) -> None:
    """
    Checkout a branch.
    
    Args:
        branch: Branch name to checkout
        create: Whether to create the branch if it doesn't exist
    """
    if create:
        run_git_command(f"git checkout -b {shlex.quote(branch)}")
    else:
        run_git_command(f"git checkout {shlex.quote(branch)}")


def push_branch(remote: str, branch: str, force: bool = False, set_upstream: bool = False) -> None:
    """
    Push a branch to remote.
    
    Args:
        remote: Remote name
        branch: Branch name
        force: Whether to force push
        set_upstream: Whether to set upstream tracking
    """
    cmd = f"git push"
    if force:
        cmd += " --force"
    if set_upstream:
        cmd += f" -u {shlex.quote(remote)} {shlex.quote(branch)}"
    else:
        cmd += f" {shlex.quote(remote)} {shlex.quote(branch)}"
    
    run_git_command(cmd)


def squash_commits_since(merge_base: str, message: str = "Squashed commits") -> None:
    """
    Squash all commits since merge_base into a single commit.
    
    Args:
        merge_base: Commit hash to squash from
        message: Commit message for the squashed commit
    """
    run_git_command(f"git reset --soft {shlex.quote(merge_base)}")
    run_git_command(f'git commit -m {shlex.quote(message)}')


def rebase_onto(upstream_master: str, branch: str) -> None:
    """
    Rebase a branch onto upstream master.
    
    Args:
        upstream_master: Upstream master branch reference
        branch: Branch to rebase
    """
    run_git_command(f"git rebase {shlex.quote(upstream_master)} {shlex.quote(branch)}")