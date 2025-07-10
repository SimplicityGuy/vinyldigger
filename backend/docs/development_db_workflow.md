# Database Development Workflow

## Overview

During development, VinylDigger uses a simplified database management approach:
- **Single initial migration**: All current models are captured in one baseline migration
- **Drop and recreate**: When model changes occur during development, we drop and recreate the database
- **Alembic for production**: Alembic remains configured for future production migrations

## Development Workflow

### Initial Setup

1. **Start the database services**:
   ```bash
   just up
   # or
   docker-compose up -d postgres redis
   ```

2. **Database is automatically created**:
   - The backend service runs `alembic upgrade head` on startup
   - This applies the initial migration that creates all tables

### Making Model Changes

When you need to change database models during development:

1. **Make your model changes** in the appropriate files under `src/models/`

2. **Drop and recreate the database**:
   ```bash
   # Stop all services
   just down

   # Remove the database volume
   docker volume rm vinyldigger_postgres_data

   # Start services again - database will be recreated
   just up
   ```

3. **Alternative: Reset database without removing volume**:
   ```bash
   # Connect to postgres container
   docker-compose exec postgres psql -U postgres

   # Drop and recreate database
   DROP DATABASE vinyldigger;
   CREATE DATABASE vinyldigger;
   \q

   # Restart backend to run migrations
   docker-compose restart backend
   ```

### Important Notes

- **No incremental migrations during development**: We maintain only the initial migration
- **Data loss**: This approach means all data is lost when recreating the database
- **Test data**: Use scripts or fixtures to reload test data after recreation

## Production Workflow (Future)

When moving to production:

1. **Generate new migration** from the current state:
   ```bash
   cd backend
   uv run alembic revision --autogenerate -m "Description of changes"
   ```

2. **Review the generated migration** carefully

3. **Apply migration**:
   ```bash
   uv run alembic upgrade head
   ```

## Database Commands Reference

### Useful Commands

```bash
# View current database state
docker-compose exec postgres psql -U postgres -d vinyldigger -c "\dt"

# Connect to database
docker-compose exec postgres psql -U postgres -d vinyldigger

# View migration history
cd backend && uv run alembic history

# Generate new migration (for production)
cd backend && uv run alembic revision --autogenerate -m "Description"

# Apply migrations
cd backend && uv run alembic upgrade head

# Downgrade migration (if needed)
cd backend && uv run alembic downgrade -1
```

### Database Connection

- **Development**: `postgresql://postgres:postgres@localhost:5432/vinyldigger`
- **Docker Internal**: `postgresql://postgres:postgres@postgres:5432/vinyldigger`

## Troubleshooting

### Migration Errors

If you encounter migration errors:

1. Check if the database exists
2. Ensure no conflicting migrations in `alembic/versions/`
3. Verify all model imports in `src/models/__init__.py`

### Clean Slate

For a completely fresh start:
```bash
just clean  # Removes all containers and volumes
just up     # Starts fresh with new database
```
