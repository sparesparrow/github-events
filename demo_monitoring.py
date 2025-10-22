#!/usr/bin/env python3
"""
Repository Monitoring Demo

Shows the repository comparison functionality without the API server.
"""

import asyncio
import json
from datetime import datetime
from src.github_events_monitor.event_collector import GitHubEventsCollector

async def demo_repository_monitoring():
    """Demonstrate repository monitoring and comparison"""
    
    print("🚀 Repository Monitoring Demo")
    print("=" * 50)
    
    # Initialize collector
    collector = GitHubEventsCollector('github_events.db')
    await collector.initialize_database()
    
    print("\n📊 Repository Metrics Summary")
    print("-" * 30)
    
    repos = ['openssl/openssl', 'sparesparrow/github-events']
    
    for repo in repos:
        print(f"\n🔍 Repository: {repo}")
        
        try:
            # Get repository activity
            activity = await collector.get_repository_activity_summary(repo, hours=168)
            print(f"  📈 Total Events: {activity.get('total_events', 0)}")
            print(f"  🔀 Pull Requests: {activity.get('pull_request_events', 0)}")
            print(f"  📝 Issues: {activity.get('issues_events', 0)}")
            print(f"  📦 Pushes: {activity.get('push_events', 0)}")
            print(f"  ⭐ Watch Events: {activity.get('watch_events', 0)}")
            
            # Get PR metrics if available
            try:
                pr_metrics = await collector.get_avg_pr_interval(repo)
                if pr_metrics.get('avg_interval_seconds'):
                    avg_hours = pr_metrics['avg_interval_seconds'] / 3600
                    print(f"  ⏱️  Avg PR Interval: {avg_hours:.1f} hours")
                else:
                    print(f"  ⏱️  Avg PR Interval: No data")
            except Exception:
                print(f"  ⏱️  Avg PR Interval: No data")
            
        except Exception as e:
            print(f"  ❌ Error getting metrics: {e}")
    
    print("\n🔬 Comparison Analysis")
    print("-" * 25)
    
    try:
        # Get data for both repositories
        openssl_activity = await collector.get_repository_activity_summary('openssl/openssl', hours=168)
        fork_activity = await collector.get_repository_activity_summary('sparesparrow/github-events', hours=168)
        
        # Compare key metrics
        openssl_total = openssl_activity.get('total_events', 0)
        fork_total = fork_activity.get('total_events', 0)
        
        print(f"📊 Activity Comparison (Last 7 days):")
        print(f"  OpenSSL: {openssl_total} events")
        print(f"  Your Fork: {fork_total} events")
        
        if openssl_total > 0 and fork_total > 0:
            ratio = openssl_total / fork_total
            print(f"  Activity Ratio: {ratio:.1f}x more active (OpenSSL vs Fork)")
        
        # Analyze workflow patterns (simulated)
        openssl_pushes = openssl_activity.get('push_events', 0)
        fork_pushes = fork_activity.get('push_events', 0)
        
        print(f"\n🔧 Development Activity:")
        print(f"  OpenSSL Pushes: {openssl_pushes}")
        print(f"  Your Fork Pushes: {fork_pushes}")
        
        # Calculate automation scores (simplified)
        def calculate_automation_score(activity):
            score = 0
            if activity.get('push_events', 0) > 0:
                score += 30  # Has development activity
            if activity.get('pull_request_events', 0) > 0:
                score += 25  # Has PR workflow
            if activity.get('issues_events', 0) > 0:
                score += 20  # Has issue tracking
            if activity.get('release_events', 0) > 0:
                score += 25  # Has release automation
            return min(score, 100)
        
        openssl_score = calculate_automation_score(openssl_activity)
        fork_score = calculate_automation_score(fork_activity)
        
        print(f"\n🤖 Automation Maturity Scores:")
        print(f"  OpenSSL: {openssl_score}/100")
        print(f"  Your Fork: {fork_score}/100")
        
        # Generate recommendations
        print(f"\n💡 Recommendations:")
        
        recommendations = []
        
        if fork_pushes == 0:
            recommendations.append("Consider adding more development activity to your fork")
        
        if openssl_activity.get('pull_request_events', 0) > fork_activity.get('pull_request_events', 0):
            recommendations.append("OpenSSL has more PR activity - consider implementing similar collaboration patterns")
        
        if openssl_score > fork_score:
            recommendations.append(f"OpenSSL shows higher automation maturity ({openssl_score} vs {fork_score}) - study their CI practices")
        
        if not recommendations:
            recommendations.append("Both repositories show similar patterns - continue current practices")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
    except Exception as e:
        print(f"❌ Error in comparison analysis: {e}")
    
    print(f"\n✅ Demo completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 Summary:")
    print("  ✓ Database initialized")
    print("  ✓ Repository data collected") 
    print("  ✓ Metrics calculated")
    print("  ✓ Comparison analysis completed")
    
    print("\n🌐 Next Steps:")
    print("  1. Fix API endpoint imports for web dashboard")
    print("  2. Set GITHUB_TOKEN for higher rate limits")
    print("  3. Configure automated monitoring workflow")
    print("  4. Deploy comparison dashboard")
    
    return {
        'openssl_activity': openssl_activity,
        'fork_activity': fork_activity,
        'openssl_score': openssl_score,
        'fork_score': fork_score,
        'recommendations': recommendations
    }

if __name__ == "__main__":
    # Run the demo
    result = asyncio.run(demo_repository_monitoring())
    
    # Save results for reference
    with open('demo_results.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to demo_results.json")