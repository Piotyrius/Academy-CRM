#!/bin/bash
set -e

echo "Starting Academy CRM entrypoint script..."

# Wait for database to be ready (optional - can be disabled with SKIP_DB_WAIT=true)
# NOTE: pg_isready may not work on Render's internal network, so this is optional
if [ "${SKIP_DB_WAIT:-false}" != "true" ] && [ -n "$DB_HOST" ]; then
    # Extract hostname from DB_HOST (handles password@host/database:port format)
    DB_HOST_CLEAN="$DB_HOST"
    
    # Remove password@ prefix if present
    if [[ "$DB_HOST_CLEAN" =~ @ ]]; then
        DB_HOST_CLEAN="${DB_HOST_CLEAN#*@}"
    fi
    
    # Remove /database suffix if present
    if [[ "$DB_HOST_CLEAN" =~ / ]]; then
        DB_HOST_CLEAN="${DB_HOST_CLEAN%%/*}"
    fi
    
    # Remove :port suffix if present
    if [[ "$DB_HOST_CLEAN" =~ : ]]; then
        DB_HOST_CLEAN="${DB_HOST_CLEAN%%:*}"
    fi
    
    # Skip if it looks like a full URL
    if [[ "$DB_HOST_CLEAN" =~ ^postgresql:// ]] || [[ "$DB_HOST_CLEAN" =~ ^postgres:// ]]; then
        echo "Skipping database wait (DB_HOST appears to be a full URL)"
    else
        echo "Waiting for database to be ready (host: $DB_HOST_CLEAN)..."
        max_attempts=10
        attempt=0
        until pg_isready -h "$DB_HOST_CLEAN" -p "${DB_PORT:-5432}" -U "$DB_USER" 2>/dev/null || [ $attempt -ge $max_attempts ]; do
            attempt=$((attempt + 1))
            if [ $((attempt % 3)) -eq 0 ]; then
                echo "Database check (attempt $attempt/$max_attempts)..."
            fi
            sleep 1
        done
        
        if [ $attempt -ge $max_attempts ]; then
            echo "⚠️  pg_isready failed, but continuing (database may still be accessible via Django)"
            echo "   To skip this check: set SKIP_DB_WAIT=true in environment variables"
        else
            echo "✅ Database is ready!"
        fi
    fi
else
    if [ "${SKIP_DB_WAIT:-false}" = "true" ]; then
        echo "Skipping database wait (SKIP_DB_WAIT=true)"
    else
        echo "Skipping database wait (DB_HOST not set)"
    fi
fi

# Run migrations (disabled by default, enable with AUTO_MIGRATE=true)
# NOTE: If using Render's Pre-Deploy Command, migrations will run there instead
# This is a fallback for non-Render deployments or if Pre-Deploy is not configured
if [ "${AUTO_MIGRATE:-false}" = "true" ]; then
    echo "Running database migrations (AUTO_MIGRATE=true)..."
    python manage.py migrate --noinput || {
        echo "WARNING: Migrations failed, but continuing..."
    }
else
    echo "Skipping migrations (AUTO_MIGRATE=false or using Pre-Deploy Command)"
    echo "  To enable: set AUTO_MIGRATE=true or use Render Pre-Deploy Command"
fi

# Collect static files (moved to runtime for faster builds)
# NOTE: If using Render's Pre-Deploy Command, static files will be collected there
# This is a fallback for non-Render deployments or if Pre-Deploy is not configured
if [ ! -d "/app/staticfiles" ] || [ -z "$(ls -A /app/staticfiles)" ] || [ "${AUTO_COLLECT_STATIC:-true}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput || true
else
    echo "Static files already collected (likely from Pre-Deploy Command), skipping..."
fi

# Execute the command passed to the container
# If no command provided, use default gunicorn command
if [ $# -eq 0 ]; then
    echo "No command provided, using default gunicorn command..."
    exec gunicorn academy_crm.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 4 --timeout 120 --access-logfile - --error-logfile -
else
    echo "Executing command: $@"
    exec "$@"
fi

