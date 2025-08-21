# Architecture Overview - C4 Model Level 1

## System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           GitHub Events Monitor                            │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │                 │    │                 │    │                         │  │
│  │   REST API      │    │   MCP Server    │    │   Background Collector  │  │
│  │   (FastAPI)     │    │   (MCP Tools)   │    │   (Async Polling)       │  │
│  │                 │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│           │                       │                       │                  │
│           │                       │                       │                  │
│           └───────────────────────┼───────────────────────┘                  │
│                                   │                                          │
│                           ┌─────────────────┐                               │
│                           │                 │                               │
│                           │   SQLite DB     │                               │
│                           │   (Events)      │                               │
│                           │                 │                               │
│                           └─────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP API Calls
                                    │ (Events Stream)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           GitHub API                                       │
│                    (api.github.com/events)                                │
│                                                                             │
│  • WatchEvent                                                               │
│  • PullRequestEvent                                                         │
│  • IssuesEvent                                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ HTTP API Calls
                                    │ (Metrics Queries)
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           End Users                                        │
│                                                                             │
│  • REST API Clients                                                        │
│  • MCP Clients (Claude Desktop, Cursor)                                    │
│  • Dashboard Applications                                                   │
│  • Monitoring Systems                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Description

### Core Components

1. **REST API (FastAPI)**
   - **Purpose**: Provides HTTP endpoints for metrics and visualizations
   - **Key Endpoints**:
     - `GET /metrics/event-counts` - Event counts by type with time offset
     - `GET /metrics/pr-interval` - Average time between pull requests
     - `GET /visualization/trending-chart` - Chart visualization (bonus)
   - **Technology**: FastAPI, Uvicorn

2. **MCP Server**
   - **Purpose**: Model Context Protocol integration for AI tools
   - **Features**: Tools, resources, and prompts for metric analysis
   - **Technology**: MCP framework, async Python

3. **Background Collector**
   - **Purpose**: Continuously polls GitHub Events API
   - **Features**: Rate limiting, ETag caching, event filtering
   - **Technology**: Async Python, HTTPX

4. **SQLite Database**
   - **Purpose**: Local storage for collected events
   - **Features**: Optimized indices, deduplication
   - **Technology**: SQLite, aiosqlite

### External Dependencies

1. **GitHub API**
   - **Endpoint**: `https://api.github.com/events`
   - **Events**: WatchEvent, PullRequestEvent, IssuesEvent
   - **Rate Limits**: 60/hour (anonymous), 5000/hour (authenticated)

2. **End Users**
   - REST API clients
   - MCP-compatible AI tools
   - Monitoring dashboards

## Data Flow

1. **Event Collection**: Background collector polls GitHub API every 5 minutes
2. **Storage**: Events are stored in SQLite with deduplication
3. **Metrics Calculation**: Real-time calculation from stored data
4. **API Response**: REST endpoints serve calculated metrics
5. **Visualization**: Chart generation for trending data

## Key Design Decisions

1. **SQLite over PostgreSQL**: Chosen for simplicity and zero-config deployment
2. **Async Architecture**: All I/O operations are asynchronous for performance
3. **Dual Interface**: Both REST API and MCP server for maximum flexibility
4. **Background Polling**: Continuous data collection without blocking API requests
5. **Rate Limiting**: Proper handling of GitHub API rate limits

## Scalability Considerations

- **Horizontal Scaling**: Multiple instances can share the same database
- **Database Migration**: Easy migration path to PostgreSQL for high volume
- **Caching**: ETag-based caching reduces API calls
- **Background Processing**: Non-blocking event collection

## Security

- **Environment Variables**: Sensitive configuration via env vars
- **Input Validation**: Pydantic models for request validation
- **Rate Limiting**: Prevents API abuse
- **No Sensitive Data**: Only public GitHub data is accessed
