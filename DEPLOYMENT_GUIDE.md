# Deployment Guide - Running on Another PC

This guide helps you set up the Academy CRM project on a new PC (work computer).

## Prerequisites

### 1. Install Python 3.11+
```powershell
# Check Python version
python --version

# Download from: https://www.python.org/downloads/
```

### 2. Install PostgreSQL 15+
```powershell
# Download from: https://www.python.org/downloads/
# Or use winget:
winget install PostgreSQL.PostgreSQL
```

### 3. Install Git (if cloning from repository)
```powershell
winget install Git.Git
```

## Setup Steps

### Step 1: Clone/Copy Project

**Option A: From Git Repository**
```powershell
git clone <repository-url>
cd Academy-CRM
```

**Option B: Copy Project Folder**
- Copy the entire `Academy-CRM` folder to the new PC
- Place it in a convenient location (e.g., `C:\Projects\Academy-CRM`)

### Step 2: Create Virtual Environment

```powershell
cd Academy-CRM
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```powershell
# Make sure venv is activated
pip install -r requirements/base.txt
```

### Step 4: Setup PostgreSQL

#### 4.1 Install PostgreSQL
- Download from: https://www.postgresql.org/download/windows/
- Install with default settings
- **Remember the password you set for postgres user!**

#### 4.2 Create Database

**Using pgAdmin:**
1. Open pgAdmin
2. Connect to PostgreSQL server
3. Right-click "Databases" → "Create" → "Database"
4. Name: `academy_crm`
5. Click "Save"

**Or using SQL:**
```sql
CREATE DATABASE academy_crm;
```

#### 4.3 Set Postgres User Password (if not already set)

In pgAdmin Query Tool:
```sql
ALTER USER postgres WITH PASSWORD 'your_password_here';
```

### Step 5: Configure Environment Variables

Create `.env` file in project root:

```env
# Database Configuration
DB_NAME=academy_crm
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here
DB_HOST=localhost
DB_PORT=5432

# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_ENV=dev
DEBUG=True

# Redis (Optional - for Celery)
REDIS_URL=redis://localhost:6379/0
USE_REDIS=False

# Media/Static Files
MEDIA_ROOT=/media
STATIC_ROOT=/staticfiles
```

**Generate Secret Key:**
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 6: Run Migrations

```powershell
.\venv\Scripts\Activate.ps1
python manage.py migrate
```

### Step 7: Create Superuser

```powershell
python manage.py createsuperuser
```

### Step 8: Collect Static Files

```powershell
python manage.py collectstatic --noinput
```

### Step 9: Run Development Server

```powershell
python manage.py runserver
```

Visit: `http://localhost:8000/api/docs/`

## Quick Setup Script

For faster setup, you can use this PowerShell script:

```powershell
# setup_new_pc.ps1
# Run this script on the new PC

Write-Host "Setting up Academy CRM..." -ForegroundColor Cyan

# 1. Create venv
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements/base.txt

# 3. Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Please update .env with your database password!" -ForegroundColor Red
}

# 4. Run migrations
python manage.py migrate

Write-Host "Setup complete! Don't forget to:" -ForegroundColor Green
Write-Host "1. Create database 'academy_crm' in PostgreSQL" -ForegroundColor Yellow
Write-Host "2. Update .env with database password" -ForegroundColor Yellow
Write-Host "3. Run: python manage.py createsuperuser" -ForegroundColor Yellow
```

## Troubleshooting

### Database Connection Issues
- Check PostgreSQL service is running: `Get-Service postgresql*`
- Verify password in `.env` matches PostgreSQL password
- Check database exists: `psql -U postgres -l`

### Module Not Found Errors
- Make sure virtual environment is activated
- Reinstall requirements: `pip install -r requirements/base.txt`

### Port Already in Use
- Change port: `python manage.py runserver 8001`
- Or find and kill process using port 8000

## Production Deployment Checklist

For production deployment:

- [ ] Set `DEBUG=False` in `.env`
- [ ] Set `DJANGO_ENV=prod`
- [ ] Generate new `DJANGO_SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` in settings
- [ ] Setup proper database backups
- [ ] Configure Redis for Celery (if using)
- [ ] Setup SSL/HTTPS
- [ ] Configure static file serving (Nginx/Apache)
- [ ] Setup logging
- [ ] Configure email backend
- [ ] Review security settings

## Files to Include When Copying

**Essential:**
- All Python files (`*.py`)
- `requirements/` folder
- `manage.py`
- `.env.example` (template)
- `README.md`
- `DEPLOYMENT_GUIDE.md` (this file)

**Don't Copy:**
- `venv/` (recreate on new PC)
- `.env` (create new with correct values)
- `db.sqlite3` (we use PostgreSQL)
- `__pycache__/` folders
- `*.pyc` files
- `media/` and `staticfiles/` (will be generated)

## Quick Reference Commands

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements/base.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver

# Collect static files
python manage.py collectstatic

# Check database connection
python test_postgres_connection.py
```
