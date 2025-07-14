#!/bin/bash
set -e

echo "Starting VinylDigger Backend..."

# Wait for database to be ready
echo "Waiting for database connection..."
while ! pg_isready -h "${POSTGRES_HOST:-localhost}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-vinyldigger}"; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

echo "Database is ready!"

# Run database migrations
echo "Running database migrations..."
cd /app
# Use system Python since we installed with --system
python -m alembic upgrade head

# Start the application
echo "Starting API server..."
# Use system Python since we installed with --system
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --access-log
