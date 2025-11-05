# Local PostgreSQL Setup (No Docker Required)

## For Development Phase

You can use PostgreSQL installed directly on your machine. Docker is optional for local development but recommended for production deployment.

## Setup Steps

### 1. Install PostgreSQL

**Windows Options:**

**Option A: Official Installer (Recommended)**
1. Download from: https://www.postgresql.org/download/windows/
2. Run the installer
3. Remember the password you set for the `postgres` user
4. Default port: 5432

**Option B: Using Chocolatey (if you have it)**
```powershell
choco install postgresql
```

**Option C: Using Winget (Windows 11/10)**
```powershell
winget install PostgreSQL.PostgreSQL
```

### 2. Start PostgreSQL Service

PostgreSQL should start automatically. If not:

```powershell
# Check if service is running
Get-Service postgresql*

# Start if needed (replace X with your version)
Start-Service postgresql-x64-15
```

### 3. Create Database

```powershell
# Connect to PostgreSQL
psql -U postgres

# In psql, create database:
CREATE DATABASE academy_crm;

# Exit psql
\q
```

Or create from command line:
```powershell
psql -U postgres -c "CREATE DATABASE academy_crm;"
```

### 4. Update .env File

Open `.env` and set:
```
DB_NAME=academy_crm
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here
DB_HOST=localhost
DB_PORT=5432
```

### 5. Run Migrations

```powershell
# Make sure you're NOT using SQLite
# Remove USE_SQLITE if set
$env:USE_SQLITE = $null

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## Verify Setup

```powershell
# Test connection
python manage.py dbshell
# Should connect to PostgreSQL
# Type \q to exit
```

## Docker for Deployment (Later)

Yes, you can use Docker for deployment even if you don't use it locally:

- **Local Development**: PostgreSQL installed locally
- **Production/Deployment**: Docker Compose (PostgreSQL + Redis + API in containers)

The `docker-compose.yml` is ready for deployment - you don't need Docker Desktop for local development.

## Summary

✅ **For Now (Development)**: Install PostgreSQL locally
✅ **For Later (Deployment)**: Use Docker Compose on your server
✅ **No Docker Desktop needed** for local development
