#!/bin/bash
set -e

echo "Starting VinylDigger backend..."

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the server
echo "Starting uvicorn server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
