#!/bin/bash
# Build Docker images with proper OCI labels

set -euo pipefail

# Get the build date in RFC 3339 format
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

# Get the git commit SHA
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Get version from pyproject.toml or package.json
# Try to extract version from backend pyproject.toml first
if [ -f "backend/pyproject.toml" ]; then
    VERSION=$(grep '^version' backend/pyproject.toml | cut -d'"' -f2 || echo "0.1.0")
elif [ -f "frontend/package.json" ]; then
    VERSION=$(grep '"version"' frontend/package.json | head -1 | cut -d'"' -f4 || echo "0.1.0")
else
    VERSION="0.1.0"
fi
# Allow override from environment
VERSION=${VERSION_OVERRIDE:-$VERSION}

echo "Building Docker images with OCI labels..."
echo "Build Date: $BUILD_DATE"
echo "VCS Ref: $VCS_REF"
echo "Version: $VERSION"

# Export variables for docker-compose
export BUILD_DATE
export VCS_REF
export VERSION

# Build specific service or all services
# Use only docker-compose.yml to ensure we build production images with labels
if [ $# -eq 0 ]; then
    echo "Building all services..."
    BUILD_DATE="$BUILD_DATE" VCS_REF="$VCS_REF" VERSION="$VERSION" docker-compose -f docker-compose.yml build
else
    echo "Building service: $1"
    BUILD_DATE="$BUILD_DATE" VCS_REF="$VCS_REF" VERSION="$VERSION" docker-compose -f docker-compose.yml build "$1"
fi

echo "Build complete!"

# Optional: Display the labels from the built images
if command -v jq &> /dev/null; then
    echo -e "\nImage labels:"
    for service in backend frontend; do
        if docker image inspect "virtualdigger-$service:latest" &>/dev/null; then
            echo -e "\n$service:"
            # Check if labels exist and are not null
            LABELS=$(docker inspect "virtualdigger-$service:latest" 2>/dev/null | jq -r '.[0].Config.Labels')
            if [ "$LABELS" != "null" ] && [ -n "$LABELS" ]; then
                docker inspect "virtualdigger-$service:latest" 2>/dev/null | jq -r '.[0].Config.Labels | to_entries | .[] | "\(.key): \(.value)"' | grep "org.opencontainers" || true
            else
                echo "No labels found (labels are null or empty)"
            fi
        fi
    done
fi

# Validate that images were built with required labels
echo -e "\nValidating OCI compliance..."
for service in backend frontend; do
    if docker image inspect "virtualdigger-$service:latest" &>/dev/null; then
        # Check if labels exist and are not null
        LABELS_JSON=$(docker inspect "virtualdigger-$service:latest" 2>/dev/null | jq -r '.[0].Config.Labels')
        if [ "$LABELS_JSON" != "null" ] && [ -n "$LABELS_JSON" ]; then
            LABELS=$(echo "$LABELS_JSON" | jq -r 'keys[]' | grep "org.opencontainers" | wc -l)
            if [ "$LABELS" -ge 8 ]; then
                echo "✓ $service: OCI compliant (found $LABELS OCI labels)"
            else
                echo "✗ $service: Missing OCI labels (found only $LABELS)"
            fi
        else
            echo "✗ $service: No labels found (build may have failed to set labels)"
        fi
    fi
done
