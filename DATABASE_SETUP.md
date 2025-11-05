# PostgreSQL Database Setup Guide

## Why PostgreSQL (Not SQLite)?

### SQLite Limitations:
- ❌ **No concurrent writes** - Only one writer at a time
- ❌ **No UUID support** - We use UUID primary keys throughout
- ❌ **Limited scalability** - Not suitable for production
- ❌ **No advanced features** - Missing full-text search, JSON fields optimization
- ❌ **File-based** - Harder to manage, backup, and scale

### PostgreSQL Advantages:
- ✅ **Concurrent access** - Multiple users, transactions
- ✅ **UUID native support** - Perfect for our schema
- ✅ **Production-ready** - Handles 100+ students, growth
- ✅ **Advanced features** - Full-text search, JSON, arrays
- ✅ **Better performance** - Indexes, query optimization
- ✅ **ACID compliance** - Data integrity guaranteed

## Setup Options

### Option 1: Docker Compose (Recommended - Easiest)

```bash
# Start PostgreSQL and Redis
docker-compose up -d db redis

# Wait a few seconds for PostgreSQL to start
# Then run migrations
python manage.py migrate
```

This automatically creates the database with:
- Database: `academy_crm`
- User: `postgres`
- Password: `postgres`
- Port: `5432`

### Option 2: Local PostgreSQL Installation

1. **Install PostgreSQL** (if not installed):
   - Windows: Download from https://www.postgresql.org/download/windows/
   - Or use: `choco install postgresql` (if you have Chocolatey)

2. **Create Database**:
   ```sql
   -- Connect to PostgreSQL
   psql -U postgres

   -- Create database
   CREATE DATABASE academy_crm;

   -- Create user (optional, or use existing postgres user)
   CREATE USER academy_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE academy_crm TO academy_user;
   ```

3. **Update .env file**:
   ```
   DB_NAME=academy_crm
   DB_USER=postgres  # or academy_user
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

### Option 3: Cloud PostgreSQL (Production)

For production, use managed PostgreSQL:
- AWS RDS
- Google Cloud SQL
- Azure Database
- DigitalOcean Managed Databases

## Quick Setup (Docker - Recommended)

```bash
# 1. Start only database (without full stack)
docker-compose up -d db redis

# 2. Verify connection
docker-compose ps

# 3. Run migrations (remove USE_SQLITE if set)
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser
```

## Verification

Test PostgreSQL connection:
```bash
python manage.py dbshell
# Should connect to PostgreSQL
# Type \q to exit
```

Or check in Django shell:
```python
python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()
>>> print("✅ PostgreSQL connected!")
```

## Troubleshooting

### Connection Refused
- Check if PostgreSQL is running: `docker-compose ps` or `pg_isready`
- Verify port 5432 is not blocked
- Check firewall settings

### Authentication Failed
- Verify password in `.env` file
- Check PostgreSQL user exists
- Try: `psql -U postgres -h localhost` to test manually

### Database Does Not Exist
- Create it: `CREATE DATABASE academy_crm;`
- Or let Docker Compose create it automatically

## Migration from SQLite to PostgreSQL

If you already have data in SQLite:

```bash
# 1. Export data from SQLite
python manage.py dumpdata > data.json

# 2. Switch to PostgreSQL (remove USE_SQLITE)
# 3. Run migrations
python manage.py migrate

# 4. Load data
python manage.py loaddata data.json
```

## Recommended: Use Docker Compose

The easiest way is to use Docker Compose - it handles everything automatically.
