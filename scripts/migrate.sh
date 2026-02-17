#!/bin/bash
set -e

echo "Running database migrations..."

# Wait for database to be ready
if [ -n "$DB_HOST" ]; then
    echo "Waiting for database to be ready..."
    until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER"; do
        echo "Database is unavailable - sleeping"
        sleep 1
    done
    echo "Database is ready!"
fi

# Run migrations
python manage.py migrate --noinput

echo "Migrations completed successfully"

