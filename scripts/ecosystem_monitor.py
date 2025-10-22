#!/usr/bin/env python3
"""
Ecosystem Monitor Script

Monitors multiple GitHub domains for events, analyzes failures, and generates reports.
Supports cross-domain cooperation and failure analysis.
"""

import os
import sys
import json
import logging
import argparse
import sqlite3
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from github_events_monitor.event_collector import GitHubEventsCollector
from github_events_monitor.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ecosystem_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ecosystem_monitor')

class DomainMonitor:
    """Monitor a specific domain for events and failures"""
    
    def __init__(self, domain: str, github_token: Optional[str] = None):
        self.domain = domain
        self.github_token = github_token
        self.collector = GitHubEventsCollector(
            db_path="database/events.db",
            github_token=github_token
        )
        
    async def fetch_domain_events(self, hours: int = 24) -> List[Dict]:
        """Fetch events for a specific domain"""
        try:
            # Use the existing collector to fetch events
            events = await self.collector.fetch_events(limit=1000)
            
            # Filter events for this domain and convert to dict
            domain_events = []
            for event in events:
                if self.domain in event.repo_name:
                    # Convert GitHubEvent to dict for compatibility
                    event_dict = {
                        'id': event.id,
                        'type': event.event_type,
                        'created_at': event.created_at.isoformat(),
                        'repo': {'name': event.repo_name},
                        'actor': {'login': event.actor_login},
                        'payload': event.payload
                    }
                    domain_events.append(event_dict)
            
            logger.info(f"Found {len(domain_events)} events for domain {self.domain}")
            return domain_events
            
        except Exception as e:
            logger.error(f"Failed to fetch events for domain {self.domain}: {e}")
            return []
    
    def analyze_domain_health(self, events: List[Dict]) -> Dict[str, Any]:
        """Analyze domain health based on events"""
        analysis = {
            'domain': self.domain,
            'total_events': len(events),
            'event_types': {},
            'recent_activity': 0,
            'issues_detected': [],
            'health_score': 100,
            'last_activity': None
        }
        
        if not events:
            analysis['health_score'] = 0
            analysis['issues_detected'].append('No recent activity')
            return analysis
        
        # Count event types
        for event in events:
            event_type = event.get('type', 'Unknown')
            analysis['event_types'][event_type] = analysis['event_types'].get(event_type, 0) + 1
        
        # Check for recent activity (last 4 hours)
        now = datetime.now(timezone.utc)
        recent_threshold = now - timedelta(hours=4)
        
        recent_events = 0
        for event in events:
            created_at = event.get('created_at', '')
            try:
                event_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if event_time > recent_threshold:
                    recent_events += 1
            except:
                continue
        
        analysis['recent_activity'] = recent_events
        
        # Set last activity
        if events:
            latest_event = max(events, key=lambda x: x.get('created_at', ''))
            analysis['last_activity'] = latest_event.get('created_at')
        
        # Calculate health score
        if recent_events == 0:
            analysis['health_score'] -= 30
            analysis['issues_detected'].append('No recent activity in last 4 hours')
        
        if len(events) < 5:
            analysis['health_score'] -= 20
            analysis['issues_detected'].append('Low event volume')
        
        # Check for error patterns
        error_events = [e for e in events if 'error' in e.get('type', '').lower() or 
                       'fail' in e.get('type', '').lower()]
        if error_events:
            analysis['health_score'] -= len(error_events) * 5
            analysis['issues_detected'].append(f'{len(error_events)} error events detected')
        
        analysis['health_score'] = max(0, analysis['health_score'])
        
        return analysis

class FailureAnalyzer:
    """Analyze failures and suggest fixes"""
    
    def __init__(self):
        self.failure_patterns = {
            'conan_error': {
                'patterns': ['conan', 'package', 'dependency', 'build'],
                'suggestions': [
                    'Check Conan package versions and compatibility',
                    'Update Conan configuration files',
                    'Verify package dependencies are available'
                ]
            },
            'fips_failure': {
                'patterns': ['fips', 'crypto', 'security', 'compliance'],
                'suggestions': [
                    'Verify FIPS compliance requirements',
                    'Check cryptographic module configuration',
                    'Update security policies and procedures'
                ]
            },
            'workflow_failure': {
                'patterns': ['workflow', 'action', 'ci', 'cd', 'pipeline'],
                'suggestions': [
                    'Review GitHub Actions workflow configuration',
                    'Check workflow dependencies and permissions',
                    'Update workflow syntax and actions'
                ]
            },
            'build_failure': {
                'patterns': ['build', 'compile', 'test', 'make', 'cmake'],
                'suggestions': [
                    'Check build environment and dependencies',
                    'Review compiler settings and flags',
                    'Update build scripts and configuration'
                ]
            }
        }
    
    def analyze_failures(self, events: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze events for failure patterns"""
        failures = []
        
        for event in events:
            event_type = event.get('type', '')
            payload = event.get('payload', {})
            
            # Check for failure indicators
            failure_indicators = []
            for pattern_name, pattern_data in self.failure_patterns.items():
                for pattern in pattern_data['patterns']:
                    if (pattern in event_type.lower() or 
                        pattern in str(payload).lower()):
                        failure_indicators.append(pattern_name)
            
            if failure_indicators:
                failure = {
                    'event_id': event.get('id'),
                    'event_type': event_type,
                    'timestamp': event.get('created_at'),
                    'repo': event.get('repo', {}).get('name'),
                    'patterns_detected': failure_indicators,
                    'suggestions': self._get_suggestions(failure_indicators),
                    'severity': self._calculate_severity(failure_indicators)
                }
                failures.append(failure)
        
        return failures
    
    def _get_suggestions(self, patterns: List[str]) -> List[str]:
        """Get suggestions for detected failure patterns"""
        suggestions = []
        for pattern in patterns:
            if pattern in self.failure_patterns:
                suggestions.extend(self.failure_patterns[pattern]['suggestions'])
        return list(set(suggestions))  # Remove duplicates
    
    def _calculate_severity(self, patterns: List[str]) -> str:
        """Calculate failure severity"""
        if 'fips_failure' in patterns:
            return 'critical'
        elif 'conan_error' in patterns or 'build_failure' in patterns:
            return 'high'
        elif 'workflow_failure' in patterns:
            return 'medium'
        else:
            return 'low'

class EcosystemMonitor:
    """Main ecosystem monitoring class"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.domains = []
        self.results = {}
        
    def add_domain(self, domain: str):
        """Add a domain to monitor"""
        self.domains.append(DomainMonitor(domain, self.github_token))
        logger.info(f"Added domain: {domain}")
    
    async def monitor_all_domains(self, hours: int = 24) -> Dict[str, Any]:
        """Monitor all configured domains"""
        logger.info(f"Starting ecosystem monitoring for {len(self.domains)} domains")
        
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'domains': {},
            'summary': {
                'total_domains': len(self.domains),
                'healthy_domains': 0,
                'unhealthy_domains': 0,
                'total_events': 0,
                'total_issues': 0,
                'critical_issues': 0
            },
            'failures': [],
            'recommendations': []
        }
        
        failure_analyzer = FailureAnalyzer()
        
        for domain_monitor in self.domains:
            logger.info(f"Monitoring domain: {domain_monitor.domain}")
            
            # Fetch events for this domain
            events = await domain_monitor.fetch_domain_events(hours)
            
            # Analyze domain health
            health_analysis = domain_monitor.analyze_domain_health(events)
            results['domains'][domain_monitor.domain] = health_analysis
            
            # Analyze failures
            failures = failure_analyzer.analyze_failures(events)
            results['failures'].extend(failures)
            
            # Update summary
            results['summary']['total_events'] += health_analysis['total_events']
            results['summary']['total_issues'] += len(health_analysis['issues_detected'])
            
            if health_analysis['health_score'] >= 80:
                results['summary']['healthy_domains'] += 1
            else:
                results['summary']['unhealthy_domains'] += 1
            
            # Count critical issues
            critical_failures = [f for f in failures if f['severity'] == 'critical']
            results['summary']['critical_issues'] += len(critical_failures)
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results)
        
        self.results = results
        return results
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Check for unhealthy domains
        unhealthy_count = results['summary']['unhealthy_domains']
        if unhealthy_count > 0:
            recommendations.append(f"Address issues in {unhealthy_count} unhealthy domains")
        
        # Check for critical issues
        critical_count = results['summary']['critical_issues']
        if critical_count > 0:
            recommendations.append(f"Immediately address {critical_count} critical issues")
        
        # Check for low activity
        low_activity_domains = [
            domain for domain, data in results['domains'].items()
            if data['recent_activity'] == 0
        ]
        if low_activity_domains:
            recommendations.append(f"Investigate low activity in: {', '.join(low_activity_domains)}")
        
        # Check for common failure patterns
        failure_types = {}
        for failure in results['failures']:
            for pattern in failure['patterns_detected']:
                failure_types[pattern] = failure_types.get(pattern, 0) + 1
        
        for pattern, count in failure_types.items():
            if count > 2:
                recommendations.append(f"Address recurring {pattern} issues ({count} occurrences)")
        
        return recommendations
    
    def generate_reports(self, output_dir: str) -> List[str]:
        """Generate various report formats"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        reports = []
        
        # JSON analysis report
        json_file = output_path / "ecosystem_analysis.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        reports.append(str(json_file))
        
        # Markdown summary
        md_file = output_path / "ecosystem_summary.md"
        with open(md_file, 'w') as f:
            f.write(self._generate_markdown_summary())
        reports.append(str(md_file))
        
        # Detailed failure report
        if self.results['failures']:
            failure_file = output_path / "failure_analysis.json"
            with open(failure_file, 'w') as f:
                json.dump(self.results['failures'], f, indent=2)
            reports.append(str(failure_file))
        
        return reports
    
    def _generate_markdown_summary(self) -> str:
        """Generate markdown summary report"""
        summary = self.results['summary']
        
        md = f"""# Ecosystem Monitoring Report

**Generated:** {self.results['timestamp']}

## Summary

- **Total Domains:** {summary['total_domains']}
- **Healthy Domains:** {summary['healthy_domains']}
- **Unhealthy Domains:** {summary['unhealthy_domains']}
- **Total Events:** {summary['total_events']}
- **Total Issues:** {summary['total_issues']}
- **Critical Issues:** {summary['critical_issues']}

## Domain Health

"""
        
        for domain, data in self.results['domains'].items():
            status = "✅ Healthy" if data['health_score'] >= 80 else "❌ Unhealthy"
            md += f"### {domain} {status}\n"
            md += f"- **Health Score:** {data['health_score']}/100\n"
            md += f"- **Total Events:** {data['total_events']}\n"
            md += f"- **Recent Activity:** {data['recent_activity']} events (last 4h)\n"
            md += f"- **Last Activity:** {data['last_activity'] or 'Unknown'}\n"
            
            if data['issues_detected']:
                md += f"- **Issues:** {', '.join(data['issues_detected'])}\n"
            
            md += "\n"
        
        # Add failures section
        if self.results['failures']:
            md += "## Failure Analysis\n\n"
            for failure in self.results['failures'][:10]:  # Limit to first 10
                md += f"### {failure['event_type']} - {failure['severity'].upper()}\n"
                md += f"- **Repository:** {failure['repo']}\n"
                md += f"- **Timestamp:** {failure['timestamp']}\n"
                md += f"- **Patterns:** {', '.join(failure['patterns_detected'])}\n"
                md += f"- **Suggestions:** {', '.join(failure['suggestions'])}\n\n"
        
        # Add recommendations
        if self.results['recommendations']:
            md += "## Recommendations\n\n"
            for i, rec in enumerate(self.results['recommendations'], 1):
                md += f"{i}. {rec}\n"
        
        return md

async def main():
    parser = argparse.ArgumentParser(description='Ecosystem Monitor')
    parser.add_argument('--domains', required=True, 
                       help='Comma-separated list of domains to monitor')
    parser.add_argument('--output-dir', default='reports',
                       help='Output directory for reports')
    parser.add_argument('--log-dir', default='logs',
                       help='Log directory')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours of data to analyze')
    parser.add_argument('--github-token', 
                       help='GitHub token for API access')
    parser.add_argument('--force-run', action='store_true',
                       help='Force run even if recent data exists')
    
    args = parser.parse_args()
    
    # Set up logging
    log_dir = Path(args.log_dir)
    log_dir.mkdir(exist_ok=True)
    
    # Initialize monitor
    monitor = EcosystemMonitor(github_token=args.github_token)
    
    # Add domains
    domains = [d.strip() for d in args.domains.split(',')]
    for domain in domains:
        monitor.add_domain(domain)
    
    # Run monitoring
    logger.info("Starting ecosystem monitoring...")
    results = await monitor.monitor_all_domains(hours=args.hours)
    
    # Generate reports
    logger.info("Generating reports...")
    reports = monitor.generate_reports(args.output_dir)
    
    logger.info(f"Monitoring complete. Reports generated: {reports}")
    
    # Print summary
    summary = results['summary']
    print(f"\nEcosystem Monitoring Summary:")
    print(f"Domains: {summary['total_domains']} (Healthy: {summary['healthy_domains']}, Unhealthy: {summary['unhealthy_domains']})")
    print(f"Events: {summary['total_events']}, Issues: {summary['total_issues']}, Critical: {summary['critical_issues']}")
    
    if summary['critical_issues'] > 0:
        print("⚠️  CRITICAL ISSUES DETECTED - Immediate attention required!")
        sys.exit(1)
    elif summary['unhealthy_domains'] > 0:
        print("⚠️  Some domains are unhealthy - Review recommended")
        sys.exit(0)
    else:
        print("✅ All domains healthy")
        sys.exit(0)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())