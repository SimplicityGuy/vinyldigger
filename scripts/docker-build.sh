#!/bin/bash
# Build Docker images with proper OCI labels

set -euo pipefail

# Get the build date in RFC 3339 format
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

# Get the git commit SHA
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Get version from pyproject.toml or package.json
VERSION=${VERSION:-0.1.0}

echo "Building Docker images with OCI labels..."
echo "Build Date: $BUILD_DATE"
echo "VCS Ref: $VCS_REF"
echo "Version: $VERSION"

# Export variables for docker-compose
export BUILD_DATE
export VCS_REF
export VERSION

# Build specific service or all services
if [ $# -eq 0 ]; then
    echo "Building all services..."
    docker-compose build
else
    echo "Building service: $1"
    docker-compose build "$1"
fi

echo "Build complete!"

# Optional: Display the labels from the built images
if command -v jq &> /dev/null; then
    echo -e "\nImage labels:"
    for service in backend frontend; do
        echo -e "\n$service:"
        docker inspect "virtualdigger-$service:latest" 2>/dev/null | jq -r '.[0].Config.Labels | to_entries | .[] | "\(.key): \(.value)"' | grep "org.opencontainers" || true
    done
fi
