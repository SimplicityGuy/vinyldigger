# Pin specific version for reproducibility
FROM python:3.13.5-slim-bookworm AS base

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
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="docker.io/library/python:3.13.5-slim-bookworm"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies and tini for proper signal handling
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    curl \
    g++ \
    gcc \
    postgresql-client \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
# Ensure no .venv directory conflicts and install base dependencies
RUN rm -rf .venv && \
    uv pip install --system -e .

# Install dev dependencies for testing
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
    uv pip install --system -e ".[dev]"; \
    fi

# Copy application code
COPY . .

# Install Playwright browsers, make startup script executable, and create non-root user
RUN python -m playwright install chromium && \
    chmod +x start.sh && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Use tini as entrypoint for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["./start.sh"]
