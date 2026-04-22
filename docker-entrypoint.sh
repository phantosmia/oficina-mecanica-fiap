#!/bin/bash
set -e

echo "Starting oficina-mecanica API container..."

# Wait for database to be ready (SQLite doesn't need this, but good practice)
echo "Initializing database..."
poetry run python -c "from app.shared.database import init_database; init_database()"

# Populate database with sample data
echo "Populating database with sample data..."
poetry run python scripts/populate_db.py

# Start the API
echo "Starting API server..."
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000