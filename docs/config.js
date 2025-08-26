// GitHub Events Monitor - Dashboard Configuration
// This file allows you to configure the dashboard data sources

window.GITHUB_EVENTS_CONFIG = {
    // Primary API endpoints for live data
    API: {
        // Auto-detect environment: use localhost for local development, disable for GitHub Pages
        BASE_URL: (window.location.protocol === 'file:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') 
            ? 'http://localhost:8000' 
            : '', // Empty for GitHub Pages - will use static files
        
        // Alternative public API endpoints (if available)
        ALTERNATIVE_URLS: [
            // Add your deployed API server URLs here
            // 'https://your-api-server.herokuapp.com',
            // 'https://your-api-server.railway.app',
            // 'http://your-vps:8000',
        ],
        
        // API endpoint paths
        ENDPOINTS: {
            health: '/health',
            eventCounts60: '/metrics/event-counts?offset_minutes=60',
            eventCounts10: '/metrics/event-counts?offset_minutes=10',
            trending: '/metrics/trending?hours=24&limit=20',
            collect: '/collect'
        }
    },

    // Static file fallbacks (for GitHub Pages when API is unavailable)
    STATIC_FALLBACK: {
        enabled: true,
        files: {
            eventCounts60: 'event_counts_60.json',
            eventCounts10: 'event_counts_10.json',
            trending: 'trending.json',
            data: 'data.json',
            status: 'data_status.json'
        }
    },

    // Dashboard behavior
    DASHBOARD: {
        // Auto-refresh interval for live data (milliseconds)
        REFRESH_INTERVAL: 30000, // 30 seconds
        
        // Connection timeout (milliseconds)
        TIMEOUT: 5000, // 5 seconds
        
        // Maximum number of repositories to show in trending
        MAX_TRENDING_REPOS: 10,
        
        // Enable debug logging
        DEBUG: true
    },

    // Instructions for setting up your own API server
    SETUP_INSTRUCTIONS: {
        local: [
            "1. Clone the repository: git clone https://github.com/sparesparrow/github-events.git",
            "2. Install dependencies: pip install -r requirements.txt",
            "3. Set environment variable: export GITHUB_TOKEN=your_token_here",
            "4. Run the API: python -m src.github_events_monitor.api",
            "5. Update API.BASE_URL above to http://localhost:8000"
        ],
        cloud: [
            "1. Deploy to Heroku, Railway, or your preferred cloud platform",
            "2. Set GITHUB_TOKEN environment variable",
            "3. Ensure CORS_ORIGINS includes https://sparesparrow.github.io",
            "4. Update API.BASE_URL above to your deployed URL"
        ]
    }
};

// Export for Node.js environments (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.GITHUB_EVENTS_CONFIG;
}
