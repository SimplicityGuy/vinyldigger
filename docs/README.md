# VinylDigger Documentation Index

Welcome to the VinylDigger documentation! This index provides quick access to all available documentation resources.

## 📚 Documentation Overview

### Getting Started
- **[Main README](../README.md)** - Project overview, features, and quick start guide
- **[Contributing Guide](../contributing.md)** - How to contribute to the project
- **[Project Context](../CLAUDE.md)** - Technical context and AI assistant configuration

### Technical Documentation
- **[API Documentation](api.md)** - Complete REST API reference with examples
- **[API Client Examples](api-examples.md)** - Example code in Python, JavaScript/TypeScript, Go, and cURL
- **[Architecture Overview](architecture.md)** - System design, components, and technical details
- **[Testing Guide](testing.md)** - Running and writing tests, CI/CD integration
- **[Deployment Guide](deployment.md)** - Production deployment instructions and best practices
- **[Performance Tuning](performance.md)** - Optimization strategies for database, API, and frontend
- **[Security Guide](security.md)** - Security best practices and implementation guidelines
- **[Monitoring & Observability](monitoring.md)** - Comprehensive monitoring, logging, and alerting setup
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and their solutions
- **[Documentation Status Report](documentation-status.md)** - Comprehensive documentation audit and verification

### Specialized Guides
- **[E2E Testing Guide](../frontend/tests/e2e/README.md)** - End-to-end testing with Playwright
- **[Database Development Workflow](../backend/docs/development_db_workflow.md)** - Database management during development
- **[Discogs OAuth Authentication](../backend/docs/discogs_auth.md)** - Setting up and using Discogs OAuth
- **[Docker OCI Labels](docker-oci-labels.md)** - Container labeling standards and best practices

## 🗺️ Quick Navigation

### For Users
1. Start with the [Main README](../README.md) for installation
2. Check the [API Documentation](api.md) for integration
3. Review the [Deployment Guide](deployment.md) for production setup

### For Developers
1. Read the [Contributing Guide](../contributing.md) first
2. Understand the [Architecture](architecture.md)
3. Learn about [Testing](testing.md)
4. Reference [Project Context](../CLAUDE.md) for development patterns

### For DevOps
1. Follow the [Deployment Guide](deployment.md)
2. Review [Docker OCI Labels](docker-oci-labels.md)
3. Understand the [Database Development Workflow](../backend/docs/development_db_workflow.md)

## 📋 Documentation Standards

### Writing Style
- Use clear, concise language
- Include code examples where helpful
- Keep documentation up-to-date with code changes
- Use proper markdown formatting

### Documentation Structure
```
docs/
├── README.md              # This file - documentation index
├── api.md                 # API reference documentation
├── api-examples.md       # API client examples in multiple languages
├── architecture.md        # System architecture and design
├── deployment.md          # Deployment and operations guide
├── testing.md            # Testing strategies and guides
├── performance.md        # Performance tuning guide
├── security.md           # Security best practices
├── monitoring.md         # Monitoring and observability guide
├── troubleshooting.md    # Common issues and solutions
└── docker-oci-labels.md  # Docker standards documentation

backend/docs/
├── development_db_workflow.md  # Database development workflow
└── discogs_auth.md            # Discogs OAuth authentication guide
```

### Updating Documentation
1. Update relevant docs when making code changes
2. Keep examples working and tested
3. Update the main README for user-facing changes
4. Add new documentation files to this index

## 🔗 External Resources

### Technologies
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/16/)
- [Docker Documentation](https://docs.docker.com/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)

### Tools
- [Just Command Runner](https://github.com/casey/just)
- [uv Package Manager](https://github.com/astral-sh/uv)
- [Pre-commit Framework](https://pre-commit.com/)
- [Playwright Testing](https://playwright.dev/)

## 🆘 Getting Help

1. **Check the documentation** - Most answers are here
2. **Search existing issues** - Someone may have had the same question
3. **Ask in an issue** - Create a new issue with your question
4. **Review examples** - The codebase includes many examples

## 📝 Documentation TODO

- [x] Add performance tuning guide
- [x] Create troubleshooting guide
- [x] Add security best practices guide
- [x] Create API client examples in multiple languages
- [x] Add monitoring and observability guide

---

*Last updated: January 2025*
