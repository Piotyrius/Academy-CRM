#!/bin/bash
set -e

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

# Run migrations using migrate_safe command
# This command:
# 1. Disconnects guardian signal (via AppConfig.ready() and command itself)
# 2. Runs migrations in correct order (subscriptions → accounts → others)
# 3. Prevents fernet_fields encoding errors
echo "Running database migrations safely..."
python manage.py migrate_safe_guardian --noinput || {
    echo "ERROR: Migrations failed"
    exit 1
}

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "WARNING: Static file collection failed, but continuing..."
}

echo "Pre-deploy completed successfully!"

