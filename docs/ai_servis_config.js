// Dashboard configuration specifically for sparesparrow/ai-servis monitoring

const AI_SERVIS_CONFIG = {
    // API Configuration
    api: {
        baseUrl: 'http://localhost:8000',
        timeout: 10000,
        retryAttempts: 3
    },
    
    // Repository Configuration
    repository: {
        name: 'sparesparrow/ai-servis',
        displayName: 'AI-Servis',
        description: 'Focused monitoring for AI-Servis repository',
        defaultTimeWindow: 168 // 1 week
    },
    
    // Monitoring Configuration
    monitoring: {
        refreshInterval: 30000, // 30 seconds for real-time monitoring
        autoRefresh: true,
        enableNotifications: true,
        
        // Key metrics to highlight
        keyMetrics: [
            'total_events',
            'health_score',
            'recent_commits',
            'security_score',
            'developer_productivity'
        ],
        
        // Alert thresholds
        alerts: {
            lowHealthScore: 50,
            highImpactCommits: 80,
            securityRiskLevel: 'medium',
            anomalyConfidence: 0.9
        }
    },
    
    // Dashboard Layout
    dashboard: {
        title: 'AI-Servis Repository Monitor',
        sections: [
            {
                id: 'overview',
                title: 'Repository Overview',
                endpoints: [
                    '/metrics/event-counts?repo=sparesparrow/ai-servis&offset_minutes=1440',
                    '/metrics/repository-activity?repo=sparesparrow/ai-servis&hours=24'
                ]
            },
            {
                id: 'health',
                title: 'Repository Health',
                endpoints: [
                    '/metrics/repository-health?repo=sparesparrow/ai-servis&hours=168'
                ]
            },
            {
                id: 'commits',
                title: 'Recent Commits',
                endpoints: [
                    '/commits/recent?repo=sparesparrow/ai-servis&hours=24&limit=10',
                    '/commits/summary?repo=sparesparrow/ai-servis&hours=168'
                ]
            },
            {
                id: 'security',
                title: 'Security Monitoring',
                endpoints: [
                    '/metrics/security-monitoring?repo=sparesparrow/ai-servis&hours=168',
                    '/metrics/event-anomalies?repo=sparesparrow/ai-servis&hours=168'
                ]
            },
            {
                id: 'productivity',
                title: 'Developer Productivity',
                endpoints: [
                    '/metrics/developer-productivity?repo=sparesparrow/ai-servis&hours=168',
                    '/monitoring/commits/authors?repo=sparesparrow/ai-servis&hours=168'
                ]
            },
            {
                id: 'deployment',
                title: 'Releases & Deployments',
                endpoints: [
                    '/metrics/release-deployment?repo=sparesparrow/ai-servis&hours=720',
                    '/metrics/releases?repo=sparesparrow/ai-servis&hours=168'
                ]
            }
        ]
    },
    
    // Visualization Configuration
    charts: {
        eventCounts: {
            type: 'bar',
            title: 'Event Counts by Type',
            colors: ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
        },
        commitActivity: {
            type: 'line',
            title: 'Commit Activity Timeline',
            timeWindow: '7d'
        },
        healthScores: {
            type: 'radar',
            title: 'Repository Health Metrics',
            metrics: ['activity', 'collaboration', 'maintenance', 'security']
        }
    },
    
    // Export Configuration
    export: {
        formats: ['json', 'csv', 'png'],
        includeRawData: true,
        filename: 'ai_servis_monitoring_export'
    }
};

// Make configuration available globally
if (typeof window !== 'undefined') {
    window.AI_SERVIS_CONFIG = AI_SERVIS_CONFIG;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AI_SERVIS_CONFIG;
}