"""
Enhanced GitHub Events Collector with database abstraction.

This collector uses the abstract database interface, allowing it to work
with both SQLite and DynamoDB backends seamlessly.
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

import httpx

from .infrastructure.database_service import DatabaseService
from .infrastructure.database_factory import create_database_manager_from_config
from .event import GitHubEvent
from .config import config

logger = logging.getLogger(__name__)


class EnhancedGitHubEventsCollector:
    """
    Enhanced GitHub Events Collector with database abstraction.
    
    This collector can work with any database backend that implements
    the database interface (SQLite, DynamoDB, etc.).
    """
    
    # Events we're interested in monitoring - expanded for comprehensive monitoring
    MONITORED_EVENTS = {
        # Core development events
        'WatchEvent',           # Stars/watching repositories
        'PullRequestEvent',     # Pull requests opened/closed/merged
        'IssuesEvent',          # Issues opened/closed/labeled
        'PushEvent',           # Code pushes to repositories
        'ForkEvent',           # Repository forks
        'CreateEvent',         # Branch/tag creation
        'DeleteEvent',         # Branch/tag deletion
        'ReleaseEvent',        # Releases published
        
        # Collaboration events
        'CommitCommentEvent',  # Comments on commits
        'IssueCommentEvent',   # Comments on issues
        'PullRequestReviewEvent',      # PR reviews
        'PullRequestReviewCommentEvent', # Comments on PR reviews
        
        # Repository management events
        'PublicEvent',         # Repository made public
        'MemberEvent',         # Collaborators added/removed
        'TeamAddEvent',        # Teams added to repositories
        
        # Security and maintenance events
        'GollumEvent',         # Wiki pages created/updated
        'DeploymentEvent',     # Deployments created
        'DeploymentStatusEvent', # Deployment status updates
        'StatusEvent',         # Commit status updates
        'CheckRunEvent',       # Check runs completed
        'CheckSuiteEvent',     # Check suites completed
        
        # GitHub-specific events
        'SponsorshipEvent',    # Sponsorship changes
        'MarketplacePurchaseEvent', # Marketplace purchases
    }
    
    def __init__(
        self,
        database_service: Optional[DatabaseService] = None,
        github_token: Optional[str] = None,
        user_agent: str = "GitHub-Events-Monitor/2.0",
        target_repositories: Optional[List[str]] = None,
    ):
        self.database_service = database_service or DatabaseService()
        self.github_token = github_token or config.github_token
        self.user_agent = user_agent
        self.api_base = "https://api.github.com"
        self.target_repositories = target_repositories or config.target_repositories
        self.last_etag: Optional[str] = None
        self.last_modified: Optional[str] = None
    
    async def initialize(self) -> None:
        """Initialize the collector and database."""
        await self.database_service.initialize()
        logger.info("Enhanced GitHub Events Collector initialized")
    
    async def close(self) -> None:
        """Close the collector and database connections."""
        await self.database_service.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check collector and database health."""
        db_health = await self.database_service.health_check()
        
        return {
            'collector_status': 'healthy',
            'database': db_health,
            'monitored_events_count': len(self.MONITORED_EVENTS),
            'target_repositories': self.target_repositories,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for GitHub API requests."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
            
        # Add conditional request headers
        if self.last_etag:
            headers["If-None-Match"] = self.last_etag
        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified
            
        return headers
    
    async def fetch_and_store_events(self, limit: Optional[int] = None) -> int:
        """
        Fetch events from GitHub API and store them in the database.
        
        Args:
            limit: Maximum number of events to fetch
            
        Returns:
            Number of events stored
        """
        events = await self.fetch_events(limit)
        
        if not events:
            return 0
        
        # Convert events to storage format
        events_data = []
        for event in events:
            events_data.append({
                'id': event.id,
                'event_type': event.event_type,
                'repo_name': event.repo_name,
                'actor_login': event.actor_login,
                'created_at': event.created_at,
                'payload': event.payload
            })
        
        # Store events
        stored_count = await self.database_service.store_events(events_data)
        
        # Process PushEvents for commit details
        push_events = [event for event in events if event.event_type == 'PushEvent']
        if push_events:
            logger.info(f"Processing {len(push_events)} PushEvents for commit details")
            for push_event in push_events:
                try:
                    await self.process_push_event_commits(push_event)
                except Exception as e:
                    logger.error(f"Failed to process commits for PushEvent {push_event.id}: {e}")
        
        return stored_count
    
    async def fetch_events(self, limit: Optional[int] = None) -> List[GitHubEvent]:
        """
        Fetch events from GitHub API.
        
        Args:
            limit: Maximum number of events to fetch
            
        Returns:
            List of GitHubEvent objects
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.api_base}/events",
                    headers=self._get_headers()
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    wait_time = max(0, reset_time - int(datetime.now().timestamp()))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                    return []
                
                # Handle not modified (cached response)
                if response.status_code == 304:
                    logger.debug("No new events (304 Not Modified)")
                    return []
                
                response.raise_for_status()
                
                # Update cache headers
                self.last_etag = response.headers.get("ETag")
                self.last_modified = response.headers.get("Last-Modified")
                
                events_data = response.json()
                events = []
                
                for event_data in events_data:
                    event_type = event_data.get("type", "")
                    
                    # Filter for events we're monitoring
                    if event_type in self.MONITORED_EVENTS:
                        events.append(GitHubEvent.from_api_data(event_data))
                        
                    # Apply limit if specified
                    if limit and len(events) >= limit:
                        break
                
                logger.info(f"Fetched {len(events)} relevant events out of {len(events_data)} total")
                return events
                
            except httpx.RequestError as e:
                logger.error(f"Request failed: {e}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return []
    
    async def process_push_event_commits(self, push_event: GitHubEvent) -> List[Dict[str, Any]]:
        """
        Process commits from a PushEvent and fetch detailed commit information.
        
        Args:
            push_event: PushEvent containing commit references
            
        Returns:
            List of processed commit data
        """
        if push_event.event_type != 'PushEvent':
            return []
        
        payload = push_event.payload
        commits = payload.get('commits', [])
        repo_name = push_event.repo_name
        branch_name = payload.get('ref', '').replace('refs/heads/', '') if payload.get('ref') else 'unknown'
        
        processed_commits = []
        
        for commit_data in commits:
            sha = commit_data.get('sha')
            if not sha:
                continue
            
            # Check if we already have this commit
            existing_commit = await self.database_service.get_commit(sha, repo_name)
            if existing_commit:
                continue  # Skip if already processed
            
            # Fetch detailed commit information from GitHub API
            detailed_commit = await self._fetch_commit_details(repo_name, sha)
            if not detailed_commit:
                continue
            
            # Process and store commit
            commit_info = await self._process_commit_data(
                detailed_commit, push_event.id, branch_name, repo_name
            )
            processed_commits.append(commit_info)
        
        return processed_commits
    
    async def _fetch_commit_details(self, repo_name: str, sha: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed commit information from GitHub API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.api_base}/repos/{repo_name}/commits/{sha}",
                    headers=self._get_headers()
                )
                
                if response.status_code == 429:
                    logger.warning(f"Rate limited fetching commit {sha}")
                    return None
                
                if response.status_code == 404:
                    logger.warning(f"Commit {sha} not found in {repo_name}")
                    return None
                
                response.raise_for_status()
                return response.json()
                
            except httpx.RequestError as e:
                logger.error(f"Failed to fetch commit {sha}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error fetching commit {sha}: {e}")
                return None
    
    async def _process_commit_data(
        self, 
        commit_data: Dict[str, Any], 
        push_event_id: str, 
        branch_name: str, 
        repo_name: str
    ) -> Dict[str, Any]:
        """Process and store detailed commit data."""
        sha = commit_data.get('sha')
        commit_info = commit_data.get('commit', {})
        author_info = commit_data.get('author', {}) or {}
        stats = commit_data.get('stats', {})
        files = commit_data.get('files', [])
        
        # Extract commit information
        commit_record = {
            'sha': sha,
            'repo_name': repo_name,
            'author_name': commit_info.get('author', {}).get('name'),
            'author_email': commit_info.get('author', {}).get('email'),
            'author_login': author_info.get('login'),
            'committer_name': commit_info.get('committer', {}).get('name'),
            'committer_email': commit_info.get('committer', {}).get('email'),
            'message': commit_info.get('message', ''),
            'commit_date': commit_info.get('author', {}).get('date'),
            'push_event_id': push_event_id,
            'branch_name': branch_name,
            'parent_shas': json.dumps([p.get('sha') for p in commit_data.get('parents', [])]),
            'stats_additions': stats.get('additions', 0),
            'stats_deletions': stats.get('deletions', 0),
            'stats_total_changes': stats.get('total', 0),
            'files_changed': len(files)
        }
        
        # Store commit record
        await self.database_service.store_commit(commit_record)
        
        # Store file changes
        files_data = []
        for file_data in files:
            files_data.append({
                'repo_name': repo_name,
                'filename': file_data.get('filename'),
                'status': file_data.get('status'),
                'additions': file_data.get('additions', 0),
                'deletions': file_data.get('deletions', 0),
                'changes': file_data.get('changes', 0),
                'patch': file_data.get('patch'),
                'previous_filename': file_data.get('previous_filename')
            })
        
        if files_data:
            await self.database_service.store_commit_files(sha, files_data)
        
        # Generate and store commit summary
        summary = await self._generate_commit_summary(commit_record, files)
        await self.database_service.store_commit_summary(summary)
        
        return {
            'commit': commit_record,
            'files': files_data,
            'summary': summary
        }
    
    async def _generate_commit_summary(
        self, 
        commit_record: Dict[str, Any], 
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate automated summary and analysis of commit changes."""
        sha = commit_record['sha']
        repo_name = commit_record['repo_name']
        message = commit_record.get('message', '')
        
        # Analyze commit message and changes
        change_categories = self._categorize_changes(message, files)
        impact_score = self._calculate_impact_score(commit_record, files)
        risk_level = self._assess_risk_level(commit_record, files, change_categories)
        breaking_changes = self._detect_breaking_changes(message, files)
        security_relevant = self._detect_security_relevance(message, files)
        performance_impact = self._assess_performance_impact(message, files)
        
        # Generate summaries
        short_summary = self._generate_short_summary(message, files, change_categories)
        detailed_summary = self._generate_detailed_summary(
            commit_record, files, change_categories, impact_score
        )
        
        return {
            'commit_sha': sha,
            'repo_name': repo_name,
            'summary_type': 'auto',
            'short_summary': short_summary,
            'detailed_summary': detailed_summary,
            'change_categories': json.dumps(change_categories),
            'impact_score': impact_score,
            'risk_level': risk_level,
            'breaking_changes': breaking_changes,
            'security_relevant': security_relevant,
            'performance_impact': performance_impact,
            'complexity_score': self._calculate_complexity_score(files)
        }
    
    def _categorize_changes(self, message: str, files: List[Dict[str, Any]]) -> List[str]:
        """Categorize the type of changes made in the commit."""
        categories = set()
        message_lower = message.lower()
        
        # Message-based categorization
        if any(word in message_lower for word in ['fix', 'bug', 'error', 'issue']):
            categories.add('bugfix')
        if any(word in message_lower for word in ['feat', 'feature', 'add', 'implement']):
            categories.add('feature')
        if any(word in message_lower for word in ['refactor', 'cleanup', 'reorganize']):
            categories.add('refactor')
        if any(word in message_lower for word in ['doc', 'readme', 'comment']):
            categories.add('documentation')
        if any(word in message_lower for word in ['test', 'spec', 'coverage']):
            categories.add('testing')
        if any(word in message_lower for word in ['perf', 'performance', 'optimize']):
            categories.add('performance')
        if any(word in message_lower for word in ['security', 'vulnerability', 'auth']):
            categories.add('security')
        if any(word in message_lower for word in ['break', 'breaking', 'major']):
            categories.add('breaking')
        
        # File-based categorization
        for file_data in files:
            filename = file_data.get('filename', '').lower()
            if any(ext in filename for ext in ['.md', '.txt', '.rst', 'readme']):
                categories.add('documentation')
            elif any(ext in filename for ext in ['test', 'spec', '.test.', '.spec.']):
                categories.add('testing')
            elif any(ext in filename for ext in ['.yml', '.yaml', '.json', 'config']):
                categories.add('configuration')
            elif any(ext in filename for ext in ['.sql', 'migration', 'schema']):
                categories.add('database')
            elif any(ext in filename for ext in ['docker', '.dockerfile', 'compose']):
                categories.add('infrastructure')
        
        return list(categories) if categories else ['other']
    
    def _calculate_impact_score(self, commit_record: Dict[str, Any], files: List[Dict[str, Any]]) -> float:
        """Calculate impact score (0-100) based on commit size and changes."""
        total_changes = commit_record.get('stats_total_changes', 0)
        files_changed = len(files)
        
        # Base score from changes
        change_score = min(50, total_changes / 10)  # Up to 50 points for changes
        file_score = min(30, files_changed * 3)     # Up to 30 points for files
        
        # Bonus for certain file types
        critical_files = sum(1 for f in files 
                            if any(pattern in f.get('filename', '').lower() 
                                  for pattern in ['package.json', 'requirements.txt', 'dockerfile', 'config']))
        critical_score = min(20, critical_files * 10)  # Up to 20 points for critical files
        
        return min(100.0, change_score + file_score + critical_score)
    
    def _assess_risk_level(
        self, 
        commit_record: Dict[str, Any], 
        files: List[Dict[str, Any]], 
        categories: List[str]
    ) -> str:
        """Assess risk level of the commit."""
        if 'breaking' in categories or 'security' in categories:
            return 'high'
        
        total_changes = commit_record.get('stats_total_changes', 0)
        files_changed = len(files)
        
        if total_changes > 500 or files_changed > 20:
            return 'high'
        elif total_changes > 100 or files_changed > 5:
            return 'medium'
        else:
            return 'low'
    
    def _detect_breaking_changes(self, message: str, files: List[Dict[str, Any]]) -> bool:
        """Detect if commit contains breaking changes."""
        message_lower = message.lower()
        breaking_keywords = ['breaking', 'break', 'major', 'incompatible', 'deprecated']
        
        if any(keyword in message_lower for keyword in breaking_keywords):
            return True
        
        # Check for API changes in certain files
        api_files = [f for f in files if any(pattern in f.get('filename', '').lower() 
                                            for pattern in ['api', 'interface', 'contract'])]
        return len(api_files) > 0
    
    def _detect_security_relevance(self, message: str, files: List[Dict[str, Any]]) -> bool:
        """Detect if commit is security-relevant."""
        message_lower = message.lower()
        security_keywords = ['security', 'vulnerability', 'auth', 'password', 'token', 'cve']
        
        if any(keyword in message_lower for keyword in security_keywords):
            return True
        
        # Check for security-related files
        security_files = [f for f in files if any(pattern in f.get('filename', '').lower() 
                                                 for pattern in ['auth', 'security', 'crypto', 'ssl', 'tls'])]
        return len(security_files) > 0
    
    def _assess_performance_impact(self, message: str, files: List[Dict[str, Any]]) -> str:
        """Assess performance impact of the commit."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['optimize', 'performance', 'faster', 'speed']):
            return 'positive'
        elif any(word in message_lower for word in ['slow', 'lag', 'bottleneck']):
            return 'negative'
        
        return 'unknown'
    
    def _calculate_complexity_score(self, files: List[Dict[str, Any]]) -> float:
        """Calculate complexity score based on file changes."""
        if not files:
            return 0.0
        
        total_complexity = 0
        for file_data in files:
            changes = file_data.get('changes', 0)
            # More changes = higher complexity
            file_complexity = min(10, changes / 10)
            total_complexity += file_complexity
        
        return min(100.0, total_complexity)
    
    def _generate_short_summary(
        self, 
        message: str, 
        files: List[Dict[str, Any]], 
        categories: List[str]
    ) -> str:
        """Generate a short summary of the commit."""
        # Use first line of commit message if available
        first_line = message.split('\n')[0] if message else ''
        if len(first_line) > 80:
            first_line = first_line[:77] + '...'
        
        if not first_line:
            # Generate based on files and categories
            if 'bugfix' in categories:
                first_line = f"Fixed issues in {len(files)} files"
            elif 'feature' in categories:
                first_line = f"Added new features in {len(files)} files"
            elif 'documentation' in categories:
                first_line = f"Updated documentation in {len(files)} files"
            else:
                first_line = f"Modified {len(files)} files"
        
        return first_line
    
    def _generate_detailed_summary(
        self, 
        commit_record: Dict[str, Any], 
        files: List[Dict[str, Any]], 
        categories: List[str], 
        impact_score: float
    ) -> str:
        """Generate a detailed summary of the commit."""
        message = commit_record.get('message', '')
        stats_additions = commit_record.get('stats_additions', 0)
        stats_deletions = commit_record.get('stats_deletions', 0)
        
        summary_parts = []
        
        # Basic stats
        summary_parts.append(f"Modified {len(files)} files with {stats_additions} additions and {stats_deletions} deletions.")
        
        # Categories
        if categories:
            summary_parts.append(f"Categories: {', '.join(categories)}")
        
        # File breakdown
        if files:
            file_types = {}
            for file_data in files:
                filename = file_data.get('filename', '')
                ext = filename.split('.')[-1] if '.' in filename else 'other'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            if file_types:
                file_breakdown = ', '.join([f"{count} {ext}" for ext, count in file_types.items()])
                summary_parts.append(f"File types: {file_breakdown}")
        
        # Impact assessment
        impact_level = 'high' if impact_score >= 70 else 'medium' if impact_score >= 40 else 'low'
        summary_parts.append(f"Impact level: {impact_level} (score: {impact_score:.1f})")
        
        # Original commit message (first few lines)
        if message:
            message_preview = '\n'.join(message.split('\n')[:3])
            if len(message_preview) > 200:
                message_preview = message_preview[:197] + '...'
            summary_parts.append(f"Original message: {message_preview}")
        
        return ' '.join(summary_parts)
    
    # High-level monitoring methods using the database service
    async def get_recent_commits(
        self, 
        repo: str, 
        hours: int = 24, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent commits for a repository with summaries."""
        return await self.database_service.get_recent_commits(
            repo=repo,
            hours_back=hours,
            limit=limit
        )
    
    async def get_repository_change_summary(
        self, 
        repo: str, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get comprehensive change summary for a repository."""
        # Get basic statistics from database service
        commits = await self.database_service.get_recent_commits(
            repo=repo,
            hours_back=hours,
            limit=1000  # Get more for accurate statistics
        )
        
        if not commits:
            return {
                'repo_name': repo,
                'analysis_period_hours': hours,
                'statistics': {
                    'total_commits': 0,
                    'unique_authors': 0,
                    'branches_active': 0,
                    'total_additions': 0,
                    'total_deletions': 0,
                    'total_files_changed': 0,
                    'avg_commit_size': 0
                },
                'quality_metrics': {
                    'breaking_changes_count': 0,
                    'security_commits_count': 0,
                    'high_impact_commits_count': 0,
                    'avg_impact_score': 0
                },
                'change_categories': {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Calculate statistics
        unique_authors = set()
        branches = set()
        total_additions = 0
        total_deletions = 0
        total_files_changed = 0
        breaking_changes = 0
        security_commits = 0
        high_impact_commits = 0
        impact_scores = []
        all_categories = []
        
        for commit in commits:
            # Basic stats
            unique_authors.add(commit.get('author_login', 'unknown'))
            branches.add(commit.get('branch_name', 'unknown'))
            total_additions += commit.get('stats_additions', 0)
            total_deletions += commit.get('stats_deletions', 0)
            total_files_changed += commit.get('files_changed', 0)
            
            # Quality metrics
            summary = commit.get('summary', {})
            if summary.get('breaking_changes'):
                breaking_changes += 1
            if summary.get('security_relevant'):
                security_commits += 1
            
            impact_score = summary.get('impact_score', 0)
            if impact_score >= 70:
                high_impact_commits += 1
            if impact_score > 0:
                impact_scores.append(impact_score)
            
            # Categories
            categories = summary.get('categories', [])
            if isinstance(categories, str):
                try:
                    categories = json.loads(categories)
                except json.JSONDecodeError:
                    categories = []
            all_categories.extend(categories)
        
        # Calculate category counts
        category_counts = {}
        for category in all_categories:
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            'repo_name': repo,
            'analysis_period_hours': hours,
            'statistics': {
                'total_commits': len(commits),
                'unique_authors': len(unique_authors),
                'branches_active': len(branches),
                'total_additions': total_additions,
                'total_deletions': total_deletions,
                'total_files_changed': total_files_changed,
                'avg_commit_size': round(
                    (total_additions + total_deletions) / len(commits), 2
                ) if commits else 0
            },
            'quality_metrics': {
                'breaking_changes_count': breaking_changes,
                'security_commits_count': security_commits,
                'high_impact_commits_count': high_impact_commits,
                'avg_impact_score': round(
                    sum(impact_scores) / len(impact_scores), 2
                ) if impact_scores else 0
            },
            'change_categories': category_counts,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def get_event_counts_by_type(self, hours_back: int = 1) -> Dict[str, int]:
        """Get event counts by type."""
        return await self.database_service.count_events_by_type(hours_back=hours_back)
    
    async def get_trending_repositories(
        self, 
        hours_back: int = 24, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending repositories."""
        return await self.database_service.get_trending_repositories(
            hours_back=hours_back,
            limit=limit
        )
    
    async def get_repository_activity(
        self, 
        repo: str, 
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get repository activity."""
        activity = await self.database_service.get_repository_activity(
            repo=repo,
            hours_back=hours_back
        )
        
        return {
            'repo_name': repo,
            'hours': hours_back,
            'total_events': activity.get('total_events', 0),
            'activity': activity.get('event_breakdown', {}),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Factory function for creating enhanced collector
def create_enhanced_collector(
    database_config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> EnhancedGitHubEventsCollector:
    """
    Create enhanced collector with specified database configuration.
    
    Args:
        database_config: Database configuration dict
        **kwargs: Additional collector configuration
        
    Returns:
        EnhancedGitHubEventsCollector instance
    """
    if database_config:
        from .infrastructure.database_factory import create_database_manager_from_config
        db_manager = create_database_manager_from_config(database_config)
        db_service = DatabaseService(db_manager)
    else:
        db_service = DatabaseService()  # Uses config from environment
    
    return EnhancedGitHubEventsCollector(
        database_service=db_service,
        **kwargs
    )