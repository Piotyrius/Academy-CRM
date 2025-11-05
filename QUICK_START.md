# Quick Start - PostgreSQL Setup

## Why PostgreSQL is Required

Your project uses:
- **UUID primary keys** - SQLite doesn't support UUIDs properly
- **Concurrent access** - Multiple admins/lecturers working simultaneously
- **Production readiness** - SQLite is not suitable for production
- **Advanced features** - Full-text search, JSON fields, etc.

## Setup Options

### Option 1: Docker Compose (Easiest - Recommended)

**Prerequisites**: Docker Desktop must be running

```powershell
# 1. Start PostgreSQL and Redis
docker-compose up -d db redis

# 2. Wait ~10 seconds for PostgreSQL to initialize
Start-Sleep -Seconds 10

# 3. Verify they're running
docker-compose ps

# 4. Run migrations (PostgreSQL will be used automatically)
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser
```

**If Docker Desktop is not running:**
- Start Docker Desktop from Start menu
- Wait for it to fully start (whale icon in system tray)
- Then run the commands above

### Option 2: Local PostgreSQL Installation

1. **Download PostgreSQL**:
   - https://www.postgresql.org/download/windows/
   - Or use: `choco install postgresql` (if you have Chocolatey)

2. **Create Database**:
   ```sql
   -- Open Command Prompt or PowerShell
   psql -U postgres
   
   -- In psql:
   CREATE DATABASE academy_crm;
   \q
   ```

3. **Update .env file** (already created):
   ```
   DB_NAME=academy_crm
   DB_USER=postgres
   DB_PASSWORD=your_postgres_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

4. **Run migrations**:
   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

### Option 3: Use SQLite Temporarily (Not Recommended)

**Only if you can't set up PostgreSQL right now:**

```powershell
# Set environment variable
$env:USE_SQLITE="True"

# Run migrations
python manage.py migrate

# Note: This is temporary - switch to PostgreSQL ASAP
```

## Verify PostgreSQL Connection

Test connection:
```powershell
python manage.py dbshell
# Should connect to PostgreSQL
# Type \q to exit
```

Or check in Python:
```python
python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()
>>> print(connection.settings_dict['ENGINE'])
# Should show: django.db.backends.postgresql
```

## Current Status

✅ **Docker Compose configuration ready**
✅ **PostgreSQL settings configured**
✅ **.env file created**

**Next Step**: 
1. Start Docker Desktop (if using Docker)
2. Run: `docker-compose up -d db redis`
3. Run: `python manage.py migrate`

## Troubleshooting

**Docker not running?**
- Start Docker Desktop application
- Wait for it to fully initialize
- Check: `docker ps` should work

**PostgreSQL connection error?**
- Verify PostgreSQL is running: `docker-compose ps` or `pg_isready`
- Check `.env` file has correct credentials
- Verify port 5432 is not blocked by firewall

**Need help?**
- See `DATABASE_SETUP.md` for detailed instructions
- Check Docker logs: `docker-compose logs db`
