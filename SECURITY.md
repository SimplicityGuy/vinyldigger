# Security Policy

## Supported Versions

VinylDigger is actively maintained, and we release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of VinylDigger seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to the project maintainer. You can find contact information in the repository.

### What to Include

Please include the following information to help us understand the nature and scope of the vulnerability:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Process

1. **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours
2. **Assessment**: We will investigate and validate the vulnerability
3. **Resolution**: We will work on a fix and coordinate the release
4. **Disclosure**: We will publicly disclose the vulnerability after the fix is released

## Security Best Practices for Users

### API Security
- Always use OAuth authentication instead of API keys when possible
- Keep your JWT tokens secure and never share them
- Use HTTPS in production environments
- Rotate your credentials regularly

### Database Security
- Use strong passwords for PostgreSQL
- Keep your database behind a firewall
- Regular backups with encryption
- Monitor database access logs

### Docker Security
- Keep Docker images updated
- Use specific version tags, not `latest`
- Run containers with minimal privileges
- Scan images for vulnerabilities regularly

### Environment Variables
- Never commit `.env` files to version control
- Use secret management systems in production
- Rotate SECRET_KEY and other sensitive values
- Use different credentials for each environment

## Security Features

VinylDigger implements several security features:

1. **Authentication & Authorization**
   - JWT-based authentication
   - OAuth 2.0 and OAuth 1.0a support
   - Session management
   - Password hashing with bcrypt

2. **Data Protection**
   - Encrypted API key storage (legacy)
   - HTTPS enforcement in production
   - CORS configuration
   - Input validation and sanitization

3. **Infrastructure Security**
   - Docker security best practices
   - Dependency vulnerability scanning
   - Pre-commit security checks
   - Regular dependency updates

## Vulnerability Disclosure Policy

We follow a responsible disclosure policy:

1. Security researchers should allow 90 days before public disclosure
2. We will work to fix vulnerabilities as quickly as possible
3. We will credit researchers who report valid vulnerabilities
4. We may request extensions for complex fixes

## Contact

For security concerns, please contact the maintainers through:
- GitHub Security Advisories (preferred)
- Direct email to repository maintainers

Thank you for helping keep VinylDigger and its users safe!
