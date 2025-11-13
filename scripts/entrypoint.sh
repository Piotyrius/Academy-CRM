#!/bin/bash
set -e

echo "Starting Academy CRM entrypoint script..."

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
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files (if not already done in build)
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Execute the command passed to the container
echo "Executing command: $@"
exec "$@"

