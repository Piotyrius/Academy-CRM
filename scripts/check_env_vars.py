"""
Script to check environment variables safely (without exposing passwords).
Run this in Render shell: python scripts/check_env_vars.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("ENVIRONMENT VARIABLES CHECK")
print("=" * 80)
print()

# Database variables
print("📊 DATABASE CONFIGURATION:")
print("-" * 80)
db_host = os.getenv('DB_HOST', 'NOT SET')
db_name = os.getenv('DB_NAME', 'NOT SET')
db_user = os.getenv('DB_USER', 'NOT SET')
db_password = os.getenv('DB_PASSWORD', 'NOT SET')
db_port = os.getenv('DB_PORT', 'NOT SET')

# Check DB_HOST format
if db_host != 'NOT SET':
    if '@' in db_host and not db_host.startswith(('postgresql://', 'postgres://')):
        print(f"⚠️  DB_HOST: {db_host[:50]}... (WARNING: Contains password!)")
        # Extract hostname
        hostname = db_host.split('@')[-1].split('/')[0].split(':')[0]
        print(f"   → Should be: {hostname}")
        print(f"   → Password part: {db_host.split('@')[0][:20]}...")
    else:
        print(f"✅ DB_HOST: {db_host}")
else:
    print(f"❌ DB_HOST: NOT SET")

print(f"✅ DB_NAME: {db_name}")
print(f"✅ DB_USER: {db_user}")
if db_password != 'NOT SET':
    print(f"✅ DB_PASSWORD: {'*' * min(len(db_password), 20)}... (hidden)")
else:
    print(f"❌ DB_PASSWORD: NOT SET")
print(f"✅ DB_PORT: {db_port}")
print()

# Application variables
print("🔧 APPLICATION CONFIGURATION:")
print("-" * 80)
print(f"DJANGO_ENV: {os.getenv('DJANGO_ENV', 'NOT SET')}")
print(f"SECRET_KEY: {'SET' if os.getenv('SECRET_KEY') else 'NOT SET'} ({'*' * 20}... if set)")
print(f"ALLOWED_HOSTS: {os.getenv('ALLOWED_HOSTS', 'NOT SET')}")
print(f"DEBUG: {os.getenv('DEBUG', 'NOT SET')}")
print()

# Redis/Celery variables
print("⚡ REDIS/CELERY CONFIGURATION:")
print("-" * 80)
redis_url = os.getenv('REDIS_URL', 'NOT SET')
celery_broker = os.getenv('CELERY_BROKER_URL', 'NOT SET')
celery_backend = os.getenv('CELERY_RESULT_BACKEND', 'NOT SET')
use_redis = os.getenv('USE_REDIS', 'NOT SET')

if redis_url != 'NOT SET':
    # Mask password in Redis URL if present
    if '@' in redis_url:
        parts = redis_url.split('@')
        if len(parts) == 2:
            masked = f"redis://***@{parts[1]}"
        else:
            masked = redis_url
    else:
        masked = redis_url
    print(f"REDIS_URL: {masked}")
else:
    print(f"REDIS_URL: NOT SET")

if celery_broker != 'NOT SET':
    if '@' in celery_broker:
        parts = celery_broker.split('@')
        if len(parts) == 2:
            masked = f"redis://***@{parts[1]}"
        else:
            masked = celery_broker
    else:
        masked = celery_broker
    print(f"CELERY_BROKER_URL: {masked}")
else:
    print(f"CELERY_BROKER_URL: NOT SET")

if celery_backend != 'NOT SET':
    if '@' in celery_backend:
        parts = celery_backend.split('@')
        if len(parts) == 2:
            masked = f"redis://***@{parts[1]}"
        else:
            masked = celery_backend
    else:
        masked = celery_backend
    print(f"CELERY_RESULT_BACKEND: {masked}")
else:
    print(f"CELERY_RESULT_BACKEND: NOT SET")

print(f"USE_REDIS: {use_redis}")
print()

# Email configuration
print("📧 EMAIL CONFIGURATION:")
print("-" * 80)
print(f"EMAIL_HOST: {os.getenv('EMAIL_HOST', 'NOT SET')}")
print(f"EMAIL_PORT: {os.getenv('EMAIL_PORT', 'NOT SET')}")
print(f"EMAIL_HOST_USER: {os.getenv('EMAIL_HOST_USER', 'NOT SET')}")
print(f"EMAIL_HOST_PASSWORD: {'SET' if os.getenv('EMAIL_HOST_PASSWORD') else 'NOT SET'}")
print(f"DEFAULT_FROM_EMAIL: {os.getenv('DEFAULT_FROM_EMAIL', 'NOT SET')}")
print()

# Recommendations
print("=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)

issues = []

if db_host != 'NOT SET' and '@' in db_host and not db_host.startswith(('postgresql://', 'postgres://')):
    issues.append("⚠️  DB_HOST contains password - should be hostname only")
    print("   Fix: In Render.com, set DB_HOST to just the hostname (e.g., 'dpg-d4b3ehmuk2gs739remf0-a')")
    print("   The password should be in DB_PASSWORD, not DB_HOST")

if db_password == 'NOT SET':
    issues.append("❌ DB_PASSWORD is not set")

if not issues:
    print("✅ All environment variables look good!")
else:
    print(f"\nFound {len(issues)} issue(s) to fix:")
    for issue in issues:
        print(f"   {issue}")

print()
print("=" * 80)

