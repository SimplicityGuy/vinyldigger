FROM python:3.13-slim AS base

# Build arguments for dynamic labels
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=0.1.0

# OCI standard labels - https://github.com/opencontainers/image-spec/blob/main/annotations.md
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.title="VinylDigger Backend" \
      org.opencontainers.image.description="Backend API for VinylDigger - vinyl record discovery tool" \
      org.opencontainers.image.authors="VinylDigger" \
      org.opencontainers.image.vendor="VinylDigger" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/SimplicityGuy/vinyldigger" \
      org.opencontainers.image.documentation="https://github.com/SimplicityGuy/vinyldigger/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    g++ \
    gcc \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv pip install --system -e .

# Install dev dependencies for testing
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
    uv pip install --system -e ".[dev]"; \
    fi

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
