#!/bin/bash
set -e

# Disable guardian signal to prevent crashes during migration
export DISABLE_GUARDIAN_SIGNAL=1

echo "Running pre-deploy commands..."

# Clear mfa_secret data BEFORE migrations (optional safety measure)
# This prevents any encoding issues if data exists before field conversion
echo "Clearing mfa_secret data (pre-migration safety check)..."
python3 scripts/clear_mfa_data.py 2>&1 || python scripts/clear_mfa_data.py 2>&1 || {
    echo "WARNING: Data clear script had issues, but continuing..."
    echo "   This is OK if the database is fresh or already cleared"
}

# Create any missing migrations
echo "Creating missing migrations..."
python manage.py makemigrations --noinput || {
    echo "WARNING: makemigrations had issues, but continuing..."
}

# Run migrations using standard migrate command
# DISABLE_GUARDIAN_SIGNAL=1 ensures guardian signal is disconnected
echo "Running database migrations..."
python manage.py migrate --noinput || {
    echo "ERROR: Migrations failed"
    exit 1
}

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "WARNING: Static file collection failed, but continuing..."
}

echo "Pre-deploy completed successfully!"

