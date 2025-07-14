# Changelog

All notable changes to VinylDigger will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Documentation improvements and organization
- CHANGELOG.md and SECURITY.md files

### Fixed
- Pre-commit hook issues in scheduler tests

## [1.0.0] - 2025-01-08

### Added
- Initial release of VinylDigger
- Marketplace search implementation - search actual listings with real prices
- Smart search integration across Discogs and eBay platforms
- Want list and collection matching with flexible sync options
- Multi-seller analysis and smart deal recommendations
- Automated search scheduling with configurable frequency (6-48+ hours)
- Editable saved searches with full CRUD functionality
- Enhanced price comparison UI with expandable album groupings
- Direct links to eBay listings and Discogs release pages
- Dashboard with 4-card stats grid and recent activity feed
- Real-time sync status with intelligent completion detection
- Profile management with editable email addresses
- OAuth authentication support for both Discogs (OAuth 1.0a) and eBay (OAuth 2.0)
- Encrypted storage for legacy API credentials
- JWT-based authentication system
- Docker containerization with OCI standard labels
- Comprehensive test suite with pytest and Vitest
- API documentation with Swagger/OpenAPI
- PostgreSQL 16 with async SQLAlchemy
- Redis 7 with Celery for background tasks
- React 19 with TypeScript 5.7 frontend
- Tailwind CSS v4 with Radix UI components

[Unreleased]: https://github.com/SimplicityGuy/vinyldigger/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/SimplicityGuy/vinyldigger/releases/tag/v1.0.0
