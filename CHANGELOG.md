# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2024-08-21

### Added
- **Comprehensive Test Suite**: 35 tests covering unit, integration, and API functionality
- **MCP Server Integration**: Full Model Context Protocol server with tools, resources, and prompts
- **Docker Support**: Complete Docker and Docker Compose configuration
- **Enhanced Documentation**: Comprehensive README with use cases and deployment guides
- **Visualization Endpoints**: Chart generation for trending repositories
- **Background Polling**: Automatic GitHub Events API polling with configurable intervals
- **Rate Limiting**: Proper GitHub API rate limit handling with ETag caching
- **Health Monitoring**: Built-in health checks and status endpoints

### Changed
- **Package Structure**: Migrated to `src/` layout for better Python packaging practices
- **Version Bump**: Updated from 0.1.0 to 0.2.1 to reflect major improvements
- **Build System**: Enhanced pyproject.toml with proper package configuration
- **Dependencies**: Updated all dependencies to latest stable versions

### Fixed
- **Build Issues**: Resolved package building and distribution problems
- **Import Errors**: Fixed module import issues in src layout
- **Test Configuration**: Proper pytest configuration for all test types
- **Docker Configuration**: Fixed Docker build and runtime issues

### Technical Improvements
- **Code Quality**: Comprehensive test coverage (35 tests passing)
- **Performance**: Optimized database queries and API responses
- **Security**: Proper environment variable handling and input validation
- **Scalability**: Support for both SQLite and future PostgreSQL migration

## [0.1.0] - Initial Release

### Added
- Basic GitHub Events API integration
- SQLite storage with basic metrics
- FastAPI REST endpoints
- Initial MCP server implementation

## Migration Guide

### From 0.1.0 to 0.2.1

1. **Package Structure**: The package now uses `src/` layout
2. **Installation**: Use `pip install github-events-monitor==0.2.1`
3. **Configuration**: Update environment variables as per `.env.template`
4. **Docker**: Use the new `docker-compose.yml` for containerized deployment

### Breaking Changes
- None - this is a backward-compatible release with significant improvements

## Release Notes

This release represents a major milestone in the GitHub Events Monitor project, providing:

- **Production Ready**: Comprehensive test suite and proper packaging
- **Developer Friendly**: Clear documentation and easy setup
- **Scalable Architecture**: Support for both development and production deployments
- **MCP Integration**: Full compatibility with Claude Desktop, Cursor, and other MCP clients

## Known Issues

- None reported in this release

## Future Roadmap

- PostgreSQL support for high-volume deployments
- Additional visualization options
- Enhanced MCP tools and resources
- Real-time event streaming
- Advanced analytics and reporting
