# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-08-26

### Added
- **New MCP Tool**: `get_health()` - REST API health status and connectivity check
- **Time-series Helper**: `get_event_counts_timeseries()` in collector for time-bucket analysis
- **Package Metadata**: Exposed `__version__ = "1.0.0"` in `__init__.py`
- **Enhanced MCP Configuration**: Added schemaVersion, version, and metadata to `.cursor/mcp.json`
- **Container Security**: Non-root user in Dockerfile for improved security
- **CI/CD Enhancements**: Added flake8 and mypy linting steps to GitHub Actions workflow
- **Code Quality Tools**: Added flake8 and mypy configurations to `pyproject.toml`
- **Git Ignore Updates**: Added `site/`, `pages_content/`, and `server.log` to `.gitignore`
- **Docker Compose**: Added `MCP_MODE` environment variable support
- **Entrypoint Hardening**: Added strict error checking and validation in `entrypoint.sh`

### Changed
- **Version Bump**: Updated from 0.2.3 to 1.0.0 for major release
- **Docker Security**: Hardened container with non-root user and improved health checks
- **Documentation**: Updated `docs/ARCHITECTURE.md` to match actual database schema
- **MCP Server**: Enhanced with new health tool and improved error handling
- **API Capabilities**: Updated `/mcp/capabilities` endpoint to include new health tool
- **Container Configuration**: Improved environment variable handling and validation

### Fixed
- **TOML Syntax**: Fixed invalid escape sequence in `pyproject.toml` mypy configuration
- **Schema Alignment**: Corrected database schema documentation to match implementation
- **Container Security**: Removed root user execution in Docker containers
- **Error Handling**: Improved validation and error messages in entrypoint script

### Technical Improvements
- **Code Quality**: Added comprehensive linting configuration (flake8, mypy)
- **Security**: Non-root container execution and improved input validation
- **Documentation**: Enhanced architecture documentation with accurate schema
- **Testing**: All 44 tests passing with 9 skipped (Docker-dependent tests)
- **Build System**: Fixed TOML parsing issues and improved build reliability

### Infrastructure
- **CI/CD Pipeline**: Enhanced with code quality checks and automated testing
- **Container Orchestration**: Improved Docker Compose configuration with MCP mode support
- **Development Tools**: Added development dependencies and linting configurations
- **Release Process**: Streamlined build and validation process

## [0.2.3] - 2025-08-25

### Added
- Initial release with core GitHub Events monitoring functionality
- REST API endpoints for metrics and visualizations
- MCP server integration for AI tool compatibility
- Docker containerization and deployment support
- Comprehensive test suite (35 tests)
- GitHub Pages visualization with Plotly charts
- Automated CI/CD pipeline with GitHub Actions

### Features
- Real-time GitHub Events collection (WatchEvent, PullRequestEvent, IssuesEvent)
- Event counts by type with time offset filtering
- Average PR interval calculations for repositories
- Trending repositories analysis
- Interactive chart visualizations
- Health monitoring endpoints
- Background polling with rate limiting

---

## Version History

- **1.0.0**: Major release with security improvements, new MCP tools, and enhanced CI/CD
- **0.2.3**: Initial production release with core monitoring functionality
