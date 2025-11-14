#!/bin/bash
set -e

echo "Starting Academy CRM entrypoint script..."

# Wait for database to be ready
if [ -n "$DB_HOST" ]; then
    echo "Waiting for database to be ready..."
    max_attempts=30
    attempt=0
    until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" || [ $attempt -ge $max_attempts ]; do
        attempt=$((attempt + 1))
        echo "Database is unavailable - sleeping (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    if [ $attempt -ge $max_attempts ]; then
        echo "WARNING: Database connection timeout, but continuing..."
    else
        echo "Database is ready!"
    fi
fi

# Run migrations (can be disabled with AUTO_MIGRATE=false)
if [ "${AUTO_MIGRATE:-true}" = "true" ]; then
    echo "Running database migrations (AUTO_MIGRATE=true)..."
    python manage.py migrate --noinput || {
        echo "WARNING: Migrations failed, but continuing..."
    }
else
    echo "Skipping migrations (AUTO_MIGRATE=false)"
fi

# Collect static files (if not already done in build)
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Execute the command passed to the container
# If no command provided, use default gunicorn command
if [ $# -eq 0 ]; then
    echo "No command provided, using default gunicorn command..."
    exec gunicorn academy_crm.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 4 --timeout 120 --access-logfile - --error-logfile -
else
    echo "Executing command: $@"
    exec "$@"
fi

