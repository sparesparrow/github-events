#!/usr/bin/env python3
"""
Enhanced Fixer Script

Analyzes domain-specific logs (Conan errors, FIPS failures, etc.) and suggests
reusable workflow tweaks and fixes. Supports cross-domain cooperation.
"""

import os
import sys
import json
import logging
import argparse
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fixer')

class LogAnalyzer:
    """Analyze various types of logs for failure patterns"""
    
    def __init__(self):
        self.patterns = {
            'conan_error': {
                'regex': [
                    r'ERROR.*conan',
                    r'conan.*ERROR',
                    r'package.*not found',
                    r'dependency.*missing',
                    r'conanfile\.txt.*error',
                    r'conan install.*failed'
                ],
                'severity': 'high',
                'category': 'dependency'
            },
            'fips_failure': {
                'regex': [
                    r'FIPS.*error',
                    r'FIPS.*failed',
                    r'crypto.*FIPS',
                    r'security.*FIPS',
                    r'compliance.*FIPS',
                    r'FIPS.*compliance'
                ],
                'severity': 'critical',
                'category': 'security'
            },
            'workflow_error': {
                'regex': [
                    r'workflow.*error',
                    r'action.*failed',
                    r'step.*failed',
                    r'ci.*error',
                    r'cd.*error',
                    r'pipeline.*failed'
                ],
                'severity': 'medium',
                'category': 'ci_cd'
            },
            'build_error': {
                'regex': [
                    r'build.*error',
                    r'compile.*error',
                    r'make.*error',
                    r'cmake.*error',
                    r'gcc.*error',
                    r'clang.*error'
                ],
                'severity': 'high',
                'category': 'build'
            },
            'test_failure': {
                'regex': [
                    r'test.*failed',
                    r'assertion.*failed',
                    r'unit.*test.*failed',
                    r'integration.*test.*failed',
                    r'pytest.*failed'
                ],
                'severity': 'medium',
                'category': 'testing'
            },
            'deployment_error': {
                'regex': [
                    r'deploy.*error',
                    r'deployment.*failed',
                    r'docker.*error',
                    r'container.*error',
                    r'kubernetes.*error'
                ],
                'severity': 'high',
                'category': 'deployment'
            }
        }
    
    def analyze_log_content(self, content: str, log_type: str = 'unknown') -> List[Dict[str, Any]]:
        """Analyze log content for failure patterns"""
        issues = []
        
        for pattern_name, pattern_data in self.patterns.items():
            for regex_pattern in pattern_data['regex']:
                matches = re.finditer(regex_pattern, content, re.IGNORECASE)
                for match in matches:
                    issue = {
                        'pattern': pattern_name,
                        'severity': pattern_data['severity'],
                        'category': pattern_data['category'],
                        'match': match.group(),
                        'line_number': content[:match.start()].count('\n') + 1,
                        'context': self._extract_context(content, match.start(), match.end()),
                        'log_type': log_type,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    issues.append(issue)
        
        return issues
    
    def _extract_context(self, content: str, start: int, end: int, context_lines: int = 3) -> str:
        """Extract context around a match"""
        lines = content.split('\n')
        match_line = content[:start].count('\n')
        
        start_line = max(0, match_line - context_lines)
        end_line = min(len(lines), match_line + context_lines + 1)
        
        context_lines = lines[start_line:end_line]
        return '\n'.join(context_lines)

class WorkflowFixer:
    """Generate workflow fixes and improvements"""
    
    def __init__(self):
        self.fix_templates = {
            'conan_error': {
                'workflow_steps': [
                    {
                        'name': 'Install Conan',
                        'run': 'pip install conan',
                        'if': 'always()'
                    },
                    {
                        'name': 'Configure Conan',
                        'run': 'conan config init',
                        'if': 'always()'
                    },
                    {
                        'name': 'Install Dependencies',
                        'run': 'conan install . --build=missing',
                        'if': 'always()'
                    }
                ],
                'environment_variables': {
                    'CONAN_USER_HOME': '${{ github.workspace }}/.conan'
                },
                'suggestions': [
                    'Add Conan installation step before build',
                    'Configure Conan with proper remotes',
                    'Use conan install with --build=missing flag',
                    'Cache Conan dependencies for faster builds'
                ]
            },
            'fips_failure': {
                'workflow_steps': [
                    {
                        'name': 'Verify FIPS Environment',
                        'run': 'openssl version -a | grep FIPS',
                        'if': 'always()'
                    },
                    {
                        'name': 'Check FIPS Compliance',
                        'run': 'python -c "import ssl; print(ssl.OPENSSL_VERSION)"',
                        'if': 'always()'
                    }
                ],
                'environment_variables': {
                    'OPENSSL_FIPS': '1'
                },
                'suggestions': [
                    'Verify FIPS-compliant OpenSSL installation',
                    'Check cryptographic module configuration',
                    'Update security policies for FIPS compliance',
                    'Use FIPS-approved algorithms only'
                ]
            },
            'workflow_error': {
                'workflow_steps': [
                    {
                        'name': 'Debug Workflow',
                        'run': 'echo "Workflow debugging information"',
                        'if': 'always()'
                    },
                    {
                        'name': 'Check Permissions',
                        'run': 'ls -la',
                        'if': 'always()'
                    }
                ],
                'suggestions': [
                    'Add debugging steps to workflow',
                    'Check GitHub Actions permissions',
                    'Verify workflow syntax and dependencies',
                    'Add error handling and retry logic'
                ]
            },
            'build_error': {
                'workflow_steps': [
                    {
                        'name': 'Install Build Dependencies',
                        'run': 'sudo apt-get update && sudo apt-get install -y build-essential',
                        'if': 'always()'
                    },
                    {
                        'name': 'Set Build Environment',
                        'run': 'export CC=gcc && export CXX=g++',
                        'if': 'always()'
                    }
                ],
                'environment_variables': {
                    'CC': 'gcc',
                    'CXX': 'g++',
                    'CFLAGS': '-O2 -Wall',
                    'CXXFLAGS': '-O2 -Wall'
                },
                'suggestions': [
                    'Install required build tools and dependencies',
                    'Set proper compiler environment variables',
                    'Check build configuration and flags',
                    'Add verbose build output for debugging'
                ]
            },
            'test_failure': {
                'workflow_steps': [
                    {
                        'name': 'Install Test Dependencies',
                        'run': 'pip install pytest pytest-cov',
                        'if': 'always()'
                    },
                    {
                        'name': 'Run Tests with Verbose Output',
                        'run': 'pytest -v --tb=short',
                        'if': 'always()'
                    }
                ],
                'suggestions': [
                    'Install test framework dependencies',
                    'Add verbose test output for debugging',
                    'Check test environment setup',
                    'Verify test data and fixtures'
                ]
            },
            'deployment_error': {
                'workflow_steps': [
                    {
                        'name': 'Verify Deployment Environment',
                        'run': 'echo "Checking deployment environment"',
                        'if': 'always()'
                    },
                    {
                        'name': 'Test Deployment',
                        'run': 'echo "Testing deployment configuration"',
                        'if': 'always()'
                    }
                ],
                'suggestions': [
                    'Verify deployment environment configuration',
                    'Check container and service health',
                    'Validate deployment scripts and permissions',
                    'Add deployment rollback procedures'
                ]
            }
        }
    
    def generate_workflow_fix(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate workflow fixes based on detected issues"""
        fixes = {
            'workflow_steps': [],
            'environment_variables': {},
            'suggestions': [],
            'priority': 'low',
            'estimated_effort': 'low'
        }
        
        # Group issues by pattern
        pattern_counts = {}
        for issue in issues:
            pattern = issue['pattern']
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        # Determine priority based on severity
        critical_issues = [i for i in issues if i['severity'] == 'critical']
        high_issues = [i for i in issues if i['severity'] == 'high']
        
        if critical_issues:
            fixes['priority'] = 'critical'
            fixes['estimated_effort'] = 'high'
        elif high_issues:
            fixes['priority'] = 'high'
            fixes['estimated_effort'] = 'medium'
        else:
            fixes['priority'] = 'medium'
            fixes['estimated_effort'] = 'low'
        
        # Generate fixes for each pattern
        for pattern, count in pattern_counts.items():
            if pattern in self.fix_templates:
                template = self.fix_templates[pattern]
                
                # Add workflow steps
                fixes['workflow_steps'].extend(template['workflow_steps'])
                
                # Add environment variables
                fixes['environment_variables'].update(template['environment_variables'])
                
                # Add suggestions
                fixes['suggestions'].extend(template['suggestions'])
        
        # Remove duplicates
        fixes['workflow_steps'] = self._deduplicate_steps(fixes['workflow_steps'])
        fixes['suggestions'] = list(set(fixes['suggestions']))
        
        return fixes
    
    def _deduplicate_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate workflow steps"""
        seen = set()
        unique_steps = []
        
        for step in steps:
            step_key = (step.get('name', ''), step.get('run', ''))
            if step_key not in seen:
                seen.add(step_key)
                unique_steps.append(step)
        
        return unique_steps

class CrossDomainCooperation:
    """Handle cross-domain cooperation and communication"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.base_url = "https://api.github.com"
    
    def trigger_repository_dispatch(self, repo: str, event_type: str, client_payload: Dict[str, Any]) -> bool:
        """Trigger a repository_dispatch event in another repository"""
        if not self.github_token:
            logger.warning("No GitHub token provided, cannot trigger repository_dispatch")
            return False
        
        url = f"{self.base_url}/repos/{repo}/dispatches"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        payload = {
            'event_type': event_type,
            'client_payload': client_payload
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully triggered {event_type} in {repo}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to trigger repository_dispatch in {repo}: {e}")
            return False
    
    def create_issue(self, repo: str, title: str, body: str, labels: List[str] = None) -> Optional[int]:
        """Create an issue in a repository"""
        if not self.github_token:
            logger.warning("No GitHub token provided, cannot create issue")
            return None
        
        url = f"{self.base_url}/repos/{repo}/issues"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        payload = {
            'title': title,
            'body': body,
            'labels': labels or []
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            issue_data = response.json()
            logger.info(f"Created issue #{issue_data['number']} in {repo}")
            return issue_data['number']
        except requests.RequestException as e:
            logger.error(f"Failed to create issue in {repo}: {e}")
            return None
    
    def publish_monitoring_data(self, data: Dict[str, Any], target_repo: str = None) -> bool:
        """Publish monitoring data to external systems or repositories"""
        # This could be extended to publish to Cloudsmith, monitoring systems, etc.
        logger.info(f"Publishing monitoring data: {len(data)} items")
        
        if target_repo:
            # Create a monitoring data issue
            title = f"Monitoring Data Update - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            body = f"```json\n{json.dumps(data, indent=2)}\n```"
            self.create_issue(target_repo, title, body, ['monitoring-data'])
        
        return True

class Fixer:
    """Main fixer class that orchestrates analysis and fixes"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.log_analyzer = LogAnalyzer()
        self.workflow_fixer = WorkflowFixer()
        self.cooperation = CrossDomainCooperation(github_token)
    
    def analyze_logs(self, log_files: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple log files for issues"""
        all_issues = []
        
        for log_file in log_files:
            if not os.path.exists(log_file):
                logger.warning(f"Log file not found: {log_file}")
                continue
            
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                log_type = Path(log_file).suffix[1:] or 'txt'
                issues = self.log_analyzer.analyze_log_content(content, log_type)
                
                for issue in issues:
                    issue['source_file'] = log_file
                
                all_issues.extend(issues)
                logger.info(f"Analyzed {log_file}: {len(issues)} issues found")
                
            except Exception as e:
                logger.error(f"Failed to analyze {log_file}: {e}")
        
        return all_issues
    
    def generate_fixes(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate fixes and recommendations based on issues"""
        fixes = self.workflow_fixer.generate_workflow_fix(issues)
        
        # Add issue summary
        fixes['issue_summary'] = {
            'total_issues': len(issues),
            'by_severity': self._count_by_severity(issues),
            'by_category': self._count_by_category(issues),
            'by_pattern': self._count_by_pattern(issues)
        }
        
        return fixes
    
    def _count_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {}
        for issue in issues:
            severity = issue['severity']
            counts[severity] = counts.get(severity, 0) + 1
        return counts
    
    def _count_by_category(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by category"""
        counts = {}
        for issue in issues:
            category = issue['category']
            counts[category] = counts.get(category, 0) + 1
        return counts
    
    def _count_by_pattern(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by pattern"""
        counts = {}
        for issue in issues:
            pattern = issue['pattern']
            counts[pattern] = counts.get(pattern, 0) + 1
        return counts
    
    def apply_cross_domain_cooperation(self, fixes: Dict[str, Any], target_repos: List[str] = None) -> Dict[str, Any]:
        """Apply cross-domain cooperation mechanisms"""
        cooperation_results = {
            'repository_dispatches': [],
            'issues_created': [],
            'data_published': False
        }
        
        if not target_repos:
            target_repos = ['sparesparrow/github-events']
        
        # Trigger repository dispatch events
        for repo in target_repos:
            payload = {
                'fixes': fixes,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'fixer'
            }
            
            success = self.cooperation.trigger_repository_dispatch(
                repo, 'fixer-analysis', payload
            )
            cooperation_results['repository_dispatches'].append({
                'repository': repo,
                'success': success
            })
        
        # Create issues for critical fixes
        if fixes['priority'] in ['critical', 'high']:
            for repo in target_repos:
                title = f"🚨 Critical Fixes Required - {fixes['priority'].upper()}"
                body = self._generate_issue_body(fixes)
                labels = ['fixer', f'priority-{fixes["priority"]}', 'automated']
                
                issue_number = self.cooperation.create_issue(repo, title, body, labels)
                if issue_number:
                    cooperation_results['issues_created'].append({
                        'repository': repo,
                        'issue_number': issue_number
                    })
        
        # Publish monitoring data
        cooperation_results['data_published'] = self.cooperation.publish_monitoring_data(
            fixes, target_repos[0] if target_repos else None
        )
        
        return cooperation_results
    
    def _generate_issue_body(self, fixes: Dict[str, Any]) -> str:
        """Generate issue body for fixes"""
        body = f"""## Fixer Analysis Report

**Priority:** {fixes['priority'].upper()}
**Estimated Effort:** {fixes['estimated_effort']}

### Issue Summary
- **Total Issues:** {fixes['issue_summary']['total_issues']}
- **By Severity:** {json.dumps(fixes['issue_summary']['by_severity'], indent=2)}
- **By Category:** {json.dumps(fixes['issue_summary']['by_category'], indent=2)}

### Suggested Workflow Steps
```yaml
steps:
"""
        
        for step in fixes['workflow_steps']:
            body += f"  - name: {step['name']}\n"
            body += f"    run: {step['run']}\n"
            if 'if' in step:
                body += f"    if: {step['if']}\n"
            body += "\n"
        
        body += f"""
### Environment Variables
```yaml
env:
"""
        for key, value in fixes['environment_variables'].items():
            body += f"  {key}: {value}\n"
        
        body += "```\n\n### Recommendations\n"
        for i, suggestion in enumerate(fixes['suggestions'], 1):
            body += f"{i}. {suggestion}\n"
        
        return body

def main():
    parser = argparse.ArgumentParser(description='Enhanced Fixer Script')
    parser.add_argument('--log-files', nargs='+', required=True,
                       help='Log files to analyze')
    parser.add_argument('--output', default='fixer_analysis.json',
                       help='Output file for analysis results')
    parser.add_argument('--github-token',
                       help='GitHub token for cross-domain cooperation')
    parser.add_argument('--target-repos', nargs='+',
                       default=['sparesparrow/github-events'],
                       help='Target repositories for cooperation')
    parser.add_argument('--cooperation', action='store_true',
                       help='Enable cross-domain cooperation')
    
    args = parser.parse_args()
    
    # Initialize fixer
    fixer = Fixer(github_token=args.github_token)
    
    # Analyze logs
    logger.info(f"Analyzing {len(args.log_files)} log files...")
    issues = fixer.analyze_logs(args.log_files)
    
    if not issues:
        logger.info("No issues found in log files")
        return
    
    # Generate fixes
    logger.info("Generating fixes...")
    fixes = fixer.generate_fixes(issues)
    
    # Apply cross-domain cooperation if enabled
    if args.cooperation:
        logger.info("Applying cross-domain cooperation...")
        cooperation_results = fixer.apply_cross_domain_cooperation(
            fixes, args.target_repos
        )
        fixes['cooperation_results'] = cooperation_results
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(fixes, f, indent=2)
    
    logger.info(f"Analysis complete. Results saved to {args.output}")
    
    # Print summary
    summary = fixes['issue_summary']
    print(f"\nFixer Analysis Summary:")
    print(f"Total Issues: {summary['total_issues']}")
    print(f"Priority: {fixes['priority']}")
    print(f"Estimated Effort: {fixes['estimated_effort']}")
    print(f"Suggestions: {len(fixes['suggestions'])}")

if __name__ == '__main__':
    main()