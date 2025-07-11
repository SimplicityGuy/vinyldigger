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

2. **Update the initial migration** (`alembic/versions/initial_schema.py`):
   - Add new columns to the appropriate table creation
   - Modify existing column definitions as needed
   - Add any new tables or enum types
   - This keeps all schema in one place during development

3. **Drop and recreate the database**:
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

### Example: Adding Search Preferences

Here's how we recently added search preference columns to the SavedSearch model:

1. **Updated the model** (`src/models/search.py`):
   ```python
   # Added to SavedSearch class
   min_record_condition: Mapped[str | None] = mapped_column(String(10), nullable=True)
   min_sleeve_condition: Mapped[str | None] = mapped_column(String(10), nullable=True)
   seller_location_preference: Mapped[str | None] = mapped_column(String(10), nullable=True)
   ```

2. **Updated the initial migration** (`alembic/versions/initial_schema.py`):
   ```python
   # Added to saved_searches table creation
   sa.Column("min_record_condition", sa.String(length=10), nullable=True),
   sa.Column("min_sleeve_condition", sa.String(length=10), nullable=True),
   sa.Column("seller_location_preference", sa.String(length=10), nullable=True),
   ```

3. **Dropped and recreated the database** using the steps above

### Important Notes

- **No incremental migrations during development**: We maintain only the initial migration
- **Data loss**: This approach means all data is lost when recreating the database
- **Test data**: Use scripts or fixtures to reload test data after recreation
- **Schema consistency**: Always ensure the initial migration matches your models exactly

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
