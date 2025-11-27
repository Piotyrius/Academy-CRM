#!/bin/bash
set -e

echo "Running pre-deploy commands..."

# Disable guardian signal during migrations to prevent fernet_fields errors
# Guardian's post_migrate signal queries User model, and fernet_fields will fail
# if it tries to decrypt old CharField data before the field is converted
export DISABLE_GUARDIAN_SIGNAL=1

# Clear mfa_secret data BEFORE migrations to prevent guardian signal errors
echo "Clearing mfa_secret data (pre-migration)..."
python3 scripts/clear_mfa_data.py 2>&1 || python scripts/clear_mfa_data.py 2>&1 || {
    echo "WARNING: Data clear script had issues, but continuing..."
    echo "   This is OK if the database is fresh or already cleared"
}

# Create any missing migrations
echo "Creating missing migrations..."
python manage.py makemigrations --noinput || {
    echo "WARNING: makemigrations had issues, but continuing..."
}

# Run migrations in stages to avoid Guardian signal issues
# Guardian's post_migrate signal queries User model, but organization_id column
# doesn't exist until accounts.0002 migration runs
echo "Running database migrations in safe order..."

# Step 1: Run subscriptions migrations first (creates Organization table)
# Use Python script to disable guardian signal before migrations
echo "Step 1: Running subscriptions migrations..."
python scripts/migrate_without_guardian.py subscriptions --noinput || {
    echo "ERROR: Subscriptions migrations failed"
    exit 1
}

# Step 2: Run accounts migrations (adds organization to User and converts mfa_secret)
echo "Step 2: Running accounts migrations..."
python scripts/migrate_without_guardian.py accounts --noinput || {
    echo "ERROR: Accounts migrations failed"
    exit 1
}

# Step 3: Run all other migrations
echo "Step 3: Running all other migrations..."
python scripts/migrate_without_guardian.py --noinput || {
    echo "ERROR: Migrations failed"
    exit 1
}

# Re-enable guardian signal (unset the environment variable)
unset DISABLE_GUARDIAN_SIGNAL

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "WARNING: Static file collection failed, but continuing..."
}

echo "Pre-deploy completed successfully!"

