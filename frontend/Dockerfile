# Base image
FROM node:22-alpine AS base

# Set environment variables
ENV NODE_ENV=production

# Development stage for running dev server
FROM base AS development

# Set environment variables
ENV NODE_ENV=development

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
RUN npm ci --only=production

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
FROM nginx:alpine AS runner

# Install wget for health check
# hadolint ignore=DL3018
RUN apk add --no-cache \
    wget \
    && rm -rf /tmp/* /var/tmp/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user for nginx
RUN adduser -D -u 1001 -g nginx nginx \
    && chown -R nginx:nginx /usr/share/nginx/html \
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

# Use nginx in foreground mode
CMD ["nginx", "-g", "daemon off;"]
