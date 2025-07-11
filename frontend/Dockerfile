# Build arguments for dynamic labels
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=0.1.0

# Pin specific version for reproducibility
FROM node:22.12-alpine3.21 AS base

# Set environment variables
ENV NODE_ENV=production

# Development stage for running dev server
FROM base AS development

# Set environment variables
ENV NODE_ENV=development

# Install curl for health checks and dumb-init for proper signal handling
# hadolint ignore=DL3018
RUN apk add --no-cache \
    curl \
    dumb-init

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci --include=dev

# Copy application files
COPY . .

# Expose port
EXPOSE 3000

# The dev command is provided by docker-compose

# Dependencies stage
FROM base AS deps

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install production dependencies only
RUN npm ci --omit=dev

# Build stage
FROM base AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies (including dev) for building
RUN npm ci --include=dev

# Copy application files
COPY . .

# Build the application
RUN npm run build

# Production stage
# Pin specific version for reproducibility
FROM nginx:1.27-alpine3.20 AS runner

# Re-declare build arguments for use in this stage
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=0.1.0

# OCI standard labels - https://github.com/opencontainers/image-spec/blob/main/annotations.md
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.title="VinylDigger Frontend" \
      org.opencontainers.image.description="Frontend application for VinylDigger - vinyl record discovery tool" \
      org.opencontainers.image.authors="VinylDigger" \
      org.opencontainers.image.vendor="VinylDigger" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/SimplicityGuy/vinyldigger" \
      org.opencontainers.image.documentation="https://github.com/SimplicityGuy/vinyldigger/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="docker.io/library/nginx:1.27-alpine3.20"

# Install wget for health check and dumb-init for proper signal handling
# hadolint ignore=DL3018
RUN apk add --no-cache \
    wget \
    dumb-init \
    && rm -rf /tmp/* /var/tmp/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Ensure proper permissions for nginx user (user already exists in nginx:alpine)
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Use dumb-init as entrypoint for proper signal handling
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Use nginx in foreground mode
CMD ["nginx", "-g", "daemon off;"]
