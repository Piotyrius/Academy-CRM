#!/bin/bash
set -e

echo "Running pre-deploy commands..."

# Fix fernet_fields data issues before migrations
echo "Checking for fernet_fields data issues..."
python scripts/fix_fernet_fields.py || {
    echo "WARNING: Data fix script had issues, but continuing..."
}

# First, create any missing migrations
echo "Creating missing migrations..."
python manage.py makemigrations --noinput || {
    echo "WARNING: makemigrations had issues, but continuing..."
}

# Run migrations in stages to avoid Guardian signal issues
# Guardian's post_migrate signal queries User model, but organization_id column
# doesn't exist until accounts.0002 migration runs
# Also, fernet_fields may have encoding issues with existing data
echo "Running database migrations in safe order..."

# Step 1: Run subscriptions migrations first (creates Organization table)
echo "Step 1: Running subscriptions migrations..."
python manage.py migrate subscriptions --noinput || {
    echo "ERROR: Subscriptions migrations failed"
    exit 1
}

# Step 2: Run accounts migrations (adds organization to User before Guardian queries it)
echo "Step 2: Running accounts migrations..."
python manage.py migrate accounts --noinput || {
    echo "ERROR: Accounts migrations failed"
    exit 1
}

# Step 3: Run all other migrations
echo "Step 3: Running all other migrations..."
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

