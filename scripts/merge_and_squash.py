#!/usr/bin/env python3
"""
merge_and_squash.py

Interactive, robust tool to:
 - check out a primary PR branch (default: PR 31)
 - pull selected other PRs (interactive selection from upstream open PRs or explicit list)
 - merge them into a working branch, resolving conflicts by calling a user-specified agent command
 - squash all changes since fork point onto a single commit rebased on upstream/master
 - resolve conflicts again if needed via agent command
 - force-push single commit to a remote branch
 - create a GitHub PR automatically (via API or `gh` CLI)

Designed to be cross-platform and easy to adapt into a larger Python-based server/tool.
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from github_events_monitor.utils.merge_utils import (
    MergeAndSquashConfig, 
    run_merge_and_squash_workflow,
    interactive_pr_selection,
    validate_environment
)
from github_events_monitor.utils.github_utils import parse_repository_url


def main():
    parser = argparse.ArgumentParser(
        description="Interactive tool to merge and squash multiple PRs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode - select PRs from list
  python scripts/merge_and_squash.py --primary-pr 31

  # Merge specific PRs
  python scripts/merge_and_squash.py --primary-pr 31 --include 32,33,34

  # Dry run mode
  python scripts/merge_and_squash.py --primary-pr 31 --dry-run

  # Custom upstream URL
  python scripts/merge_and_squash.py --primary-pr 31 --upstream-url git@github.com:owner/repo.git
        """
    )
    
    parser.add_argument(
        "--primary-pr",
        type=int,
        help="Primary PR number to start with",
        default=31
    )
    parser.add_argument(
        "--include",
        help="Comma-separated list of additional PR numbers to include",
        default=""
    )
    parser.add_argument(
        "--upstream-url",
        help="Upstream repository URL",
        default=os.getenv("UPSTREAM_URL", "git@github.com:sparesparrow/openssl-tools.git")
    )
    parser.add_argument(
        "--upstream-remote",
        help="Upstream remote name",
        default=os.getenv("UPSTREAM_REMOTE", "upstream")
    )
    parser.add_argument(
        "--origin-remote", 
        help="Origin remote name",
        default=os.getenv("ORIGIN_REMOTE", "origin")
    )
    parser.add_argument(
        "--cursor-cmd-fix",
        help="Cursor agent command for conflict resolution",
        default=os.getenv("CURSOR_CMD_FIX", 'cursor-agent -f agent "fix conflicts and complete merge/rebase"')
    )
    parser.add_argument(
        "--cursor-cmd-ack",
        help="Cursor agent command for testing and validation",
        default=os.getenv("CURSOR_CMD_ACK", 'cursor-agent -f agent "use ack tool to test and fix all workflows"')
    )
    parser.add_argument(
        "--github-token",
        help="GitHub API token",
        default=os.getenv("GITHUB_TOKEN")
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactively select additional PRs from open PRs list"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate environment and exit"
    )
    
    args = parser.parse_args()
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    if args.validate_only:
        print("Environment validation passed")
        return
    
    # Parse additional PRs
    additional_prs = []
    if args.include:
        try:
            additional_prs = [int(x.strip()) for x in args.include.split(",") if x.strip()]
        except ValueError:
            print("ERROR: Invalid PR numbers in --include")
            sys.exit(1)
    
    # Interactive PR selection
    if args.interactive and not additional_prs:
        try:
            owner, repo = parse_repository_url(args.upstream_url)
            additional_prs = interactive_pr_selection(owner, repo, args.github_token)
        except Exception as e:
            print(f"Error in interactive selection: {e}")
            sys.exit(1)
    
    # Create configuration
    config = MergeAndSquashConfig(
        upstream_remote=args.upstream_remote,
        origin_remote=args.origin_remote,
        upstream_url=args.upstream_url,
        cursor_cmd_fix=args.cursor_cmd_fix,
        cursor_cmd_ack=args.cursor_cmd_ack,
        github_token=args.github_token,
        dry_run=args.dry_run
    )
    
    # Run workflow
    print(f"Starting merge and squash workflow...")
    print(f"Primary PR: #{args.primary_pr}")
    if additional_prs:
        print(f"Additional PRs: {additional_prs}")
    print(f"Upstream URL: {args.upstream_url}")
    print(f"Dry run: {args.dry_run}")
    
    pr_info = run_merge_and_squash_workflow(
        primary_pr=args.primary_pr,
        additional_prs=additional_prs if additional_prs else None,
        upstream_url=args.upstream_url,
        config=config
    )
    
    if pr_info:
        print(f"\n✅ Workflow completed successfully!")
        if 'url' in pr_info:
            print(f"Created PR: {pr_info['url']}")
    else:
        print(f"\n❌ Workflow failed or was cancelled")
        sys.exit(1)


if __name__ == "__main__":
    main()