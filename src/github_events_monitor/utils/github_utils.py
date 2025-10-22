"""
GitHub Utilities Module

Provides reusable functions for GitHub API interactions, PR management, and CLI operations.
Designed to be consistent with the existing codebase patterns.
"""

import json
import os
import shutil
import subprocess
import shlex
from typing import List, Optional, Dict, Any

try:
    import requests  # only required for GitHub API flow
except Exception:
    requests = None  # we'll fallback to `gh` CLI if requests not present


GITHUB_API_BASE = "https://api.github.com"


def list_open_prs(owner: str, repo: str, token: Optional[str] = None, per_page: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch open PRs via GitHub API. Requires requests library.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub API token
        per_page: Number of PRs per page
        
    Returns:
        List of PR dictionaries
        
    Raises:
        RuntimeError: If requests library is not available
    """
    if requests is None:
        raise RuntimeError("requests library is required for listing PRs via GitHub API. Install with `pip install requests` or use --include to pass PR numbers manually.")
    
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls?state=open&per_page={per_page}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def create_github_pr(owner: str, repo: str, head: str, base: str, title: str, body: str = "", token: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a PR via GitHub API.
    
    Args:
        owner: Repository owner
        repo: Repository name
        head: Head branch (must be in the form forkOwner:branch or branch if same repo)
        base: Base branch
        title: PR title
        body: PR body
        token: GitHub API token
        
    Returns:
        Created PR dictionary
        
    Raises:
        RuntimeError: If requests library is not available
    """
    if requests is None:
        raise RuntimeError("requests is required to create PR via GitHub API.")
    
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    payload = {"title": title, "head": head, "base": base, "body": body}
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    r.raise_for_status()
    return r.json()


def create_pr_with_gh_cli(remote: str, branch: str, base: str, title: str, body: str = "") -> Optional[Dict[str, Any]]:
    """
    Create PR using GitHub CLI 'gh' if available.
    
    Args:
        remote: Remote name
        branch: Branch name
        base: Base branch
        title: PR title
        body: PR body
        
    Returns:
        Parsed JSON output if successful, None otherwise
    """
    if shutil.which("gh") is None:
        return None
    
    # Push branch first if not present on remote
    from .git_utils import push_branch
    push_branch(remote, branch, set_upstream=True)
    
    # gh pr create --title "..." --body "..." --base master --head <remote>:<branch> --fill --json url
    head_ref = f"{remote}:{branch}"
    try:
        # create and get URL
        cmd = f"gh pr create --head {shlex.quote(head_ref)} --base {shlex.quote(base)} --title {shlex.quote(title)} --body {shlex.quote(body)} --json url"
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        parsed = json.loads(result.stdout.strip())
        return parsed
    except subprocess.CalledProcessError:
        print("gh pr create failed; please create PR manually.", file=sys.stderr)
        return None


def get_current_user_login_from_token(token: str) -> Optional[str]:
    """
    Get authenticated username from GitHub API token.
    
    Args:
        token: GitHub API token
        
    Returns:
        Username if successful, None otherwise
    """
    if requests is None:
        return None
    
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(f"{GITHUB_API_BASE}/user", headers=headers)
    if r.status_code == 200:
        return r.json().get("login")
    return None


def get_repository_info(owner: str, repo: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get repository information via GitHub API.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub API token
        
    Returns:
        Repository information dictionary
    """
    if requests is None:
        raise RuntimeError("requests library is required for GitHub API operations.")
    
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_pr_info(owner: str, repo: str, pr_number: int, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get pull request information via GitHub API.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        token: GitHub API token
        
    Returns:
        PR information dictionary
    """
    if requests is None:
        raise RuntimeError("requests library is required for GitHub API operations.")
    
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def is_gh_cli_available() -> bool:
    """
    Check if GitHub CLI is available.
    
    Returns:
        True if gh CLI is available, False otherwise
    """
    return shutil.which("gh") is not None


def run_gh_command(cmd: str, capture: bool = True) -> subprocess.CompletedProcess:
    """
    Run a GitHub CLI command.
    
    Args:
        cmd: Command to run (without 'gh' prefix)
        capture: Whether to capture output
        
    Returns:
        CompletedProcess object
    """
    full_cmd = f"gh {cmd}"
    print(f"+ {full_cmd}")
    
    if capture:
        return subprocess.run(full_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    else:
        return subprocess.run(full_cmd, shell=True, check=True)


def get_gh_auth_status() -> Dict[str, Any]:
    """
    Get GitHub CLI authentication status.
    
    Returns:
        Authentication status dictionary
    """
    try:
        result = run_gh_command("auth status --json", capture=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        return {"authenticated": False, "error": "Not authenticated"}


def parse_repository_url(url: str) -> tuple[str, str]:
    """
    Parse a GitHub repository URL to extract owner and repo name.
    
    Args:
        url: Repository URL (https://github.com/owner/repo or git@github.com:owner/repo.git)
        
    Returns:
        Tuple of (owner, repo)
    """
    if url.startswith("https://github.com/"):
        parts = url.replace("https://github.com/", "").rstrip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    elif url.startswith("git@github.com:"):
        parts = url.replace("git@github.com:", "").replace(".git", "").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    
    raise ValueError(f"Unable to parse repository URL: {url}")


def get_default_branch(owner: str, repo: str, token: Optional[str] = None) -> str:
    """
    Get the default branch of a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub API token
        
    Returns:
        Default branch name
    """
    repo_info = get_repository_info(owner, repo, token)
    return repo_info.get("default_branch", "main")