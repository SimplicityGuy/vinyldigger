# Changelog

All notable changes to VinylDigger will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Marketplace search implementation - search actual listings with real prices
- Editable saved searches with full CRUD functionality
- Enhanced price comparison UI with expandable album groupings
- Direct links to eBay listings and Discogs release pages
- Dashboard improvements with 4-card stats grid and recent activity feed
- Real-time sync status with intelligent completion detection
- Profile management with editable email addresses
- OAuth authentication support for both Discogs (OAuth 1.0a) and eBay (OAuth 2.0)
- Backend testing guide documentation
- Comprehensive documentation updates and cleanup

### Changed
- Switched from Discogs catalog database search to marketplace search
- Improved search result data structure with listing IDs and release IDs
- Enhanced seller analysis with complete marketplace data
- Updated Python to 3.13 with Redis type annotation fixes
- Improved Docker builds with OCI standard labels compliance
- Enhanced API documentation with new sync endpoints

### Fixed
- Member Since display in user settings
- Redis type annotation issues for Python 3.13 compatibility
- Foreign key validation with proper enum usage
- OAuth token length support (5000 characters)
- Platform naming consistency (lowercase in backend)
- Pre-commit hook issues in scheduler tests

### Security
- OAuth authentication implementation replacing API keys
- Encrypted storage for legacy API credentials
- JWT token security enhancements

## [1.0.0] - 2025-01-01

### Added
- Initial release of VinylDigger
- Smart search integration across Discogs and eBay
- Want list and collection matching
- Multi-seller analysis and deal recommendations
- Automated search scheduling
- User authentication and authorization
- Docker containerization
- Comprehensive test suite
- API documentation with Swagger/OpenAPI

[Unreleased]: https://github.com/SimplicityGuy/vinyldigger/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/SimplicityGuy/vinyldigger/releases/tag/v1.0.0
