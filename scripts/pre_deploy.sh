#!/bin/bash
set -e

echo "Running pre-deploy commands..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Pre-deploy completed successfully!"

