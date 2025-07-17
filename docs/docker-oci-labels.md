# Docker OCI Labels

*Last updated: July 2025*

This project implements [OCI (Open Container Initiative) standard labels](https://github.com/opencontainers/image-spec/blob/main/annotations.md) for all Docker images to provide consistent metadata.

## Implemented Labels

Each Docker image includes the following OCI standard labels:

- `org.opencontainers.image.created` - Date and time the image was built (RFC 3339)
- `org.opencontainers.image.title` - Human-readable title of the image
- `org.opencontainers.image.description` - Human-readable description
- `org.opencontainers.image.authors` - Contact details of the people responsible
- `org.opencontainers.image.vendor` - Name of the distributing entity
- `org.opencontainers.image.version` - Version of the packaged software
- `org.opencontainers.image.revision` - Source control revision identifier (git commit SHA)
- `org.opencontainers.image.source` - URL to the source code repository
- `org.opencontainers.image.documentation` - URL to documentation
- `org.opencontainers.image.licenses` - License(s) under which the software is distributed
- `org.opencontainers.image.base.name` - Base image reference for better traceability

## Building Images with Labels

### Local Development

When building images locally, use the provided build script:

```bash
./scripts/docker-build.sh
```

Or build manually with docker-compose:

```bash
# The build arguments are automatically set in docker-compose.yml
docker-compose build
```

### Manual Docker Build

If building directly with Docker, provide the build arguments:

```bash
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=0.1.0 \
  -t vinyldigger-backend \
  ./backend
```

### CI/CD

GitHub Actions automatically sets these labels when building and pushing images. The workflow uses:
- `BUILD_DATE` from the metadata action's created timestamp
- `VCS_REF` from the GitHub SHA
- `VERSION` from git tags or branch names

## Viewing Labels

To inspect the labels on a built image:

```bash
# View all labels
docker inspect vinyldigger-backend:latest | jq '.[0].Config.Labels'

# View only OCI labels
docker inspect vinyldigger-backend:latest | jq -r '.[0].Config.Labels | to_entries | .[] | select(.key | startswith("org.opencontainers")) | "\(.key): \(.value)"'
```

## Benefits

- **Traceability**: Know exactly which commit an image was built from
- **Versioning**: Clear version information for deployment tracking
- **Documentation**: Direct links to source code and documentation
- **Compliance**: Industry-standard metadata format
- **Automation**: Tools can parse these labels for automated workflows

## Docker Best Practices

Our Dockerfiles implement several best practices:

### Security & Performance
- **Pinned base image versions** for reproducibility
- **Non-root users** for both backend (appuser) and frontend (nginx)
- **Multi-stage builds** to minimize final image size
- **Proper signal handling** with tini (backend) and dumb-init (frontend)
- **Health checks** for all services
- **DEBIAN_FRONTEND=noninteractive** for unattended installs

### Build Optimization
- **Layer caching optimization** by copying dependency files first
- **Minimal dependencies** - only install what's needed
- **Clean package manager caches** to reduce image size
- **.dockerignore files** to exclude unnecessary files

### Configuration
- **Environment variable support** for runtime configuration
- **Build arguments** for dynamic labeling
- **Hadolint compliance** with documented exceptions

### Validation
The build script automatically validates OCI compliance:

```bash
./scripts/docker-build.sh
# Output includes:
# ✓ backend: OCI compliant (found 11 OCI labels)
# ✓ frontend: OCI compliant (found 11 OCI labels)
```
