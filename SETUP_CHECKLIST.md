# Setup Checklist - New PC

Use this checklist when setting up Academy CRM on a new PC.

## Pre-Installation

- [ ] Python 3.11+ installed (`python --version`)
- [ ] PostgreSQL 15+ installed
- [ ] Git installed (if cloning from repository)
- [ ] Project files copied/cloned to new PC

## Installation Steps

### 1. Virtual Environment
- [ ] Navigate to project directory
- [ ] Run: `python -m venv venv`
- [ ] Activate: `.\venv\Scripts\Activate.ps1`

### 2. Dependencies
- [ ] Run: `pip install -r requirements/base.txt`
- [ ] Verify no errors

### 3. PostgreSQL Setup
- [ ] PostgreSQL service running
- [ ] Database `academy_crm` created
- [ ] Postgres user password set (if needed)
- [ ] Test connection: `python test_postgres_connection.py`

### 4. Configuration
- [ ] `.env` file created (from `.env.example`)
- [ ] Database credentials updated in `.env`
- [ ] `DJANGO_SECRET_KEY` generated and updated
- [ ] Other settings reviewed (debug, hosts, etc.)

### 5. Database Migration
- [ ] Run: `python manage.py migrate`
- [ ] Verify no errors

### 6. Superuser
- [ ] Run: `python manage.py createsuperuser`
- [ ] Created admin user

### 7. Static Files
- [ ] Run: `python manage.py collectstatic --noinput`

### 8. Test Server
- [ ] Run: `python manage.py runserver`
- [ ] Visit: `http://localhost:8000/api/docs/`
- [ ] Swagger UI loads correctly

## Quick Setup Script

You can use the automated script:

```powershell
.\setup_new_pc.ps1
```

Then follow the manual steps for PostgreSQL setup.

## Verification

After setup, verify:

- [ ] Can connect to database
- [ ] Server starts without errors
- [ ] Swagger UI accessible
- [ ] Can login to admin panel
- [ ] Can create test data

## Common Issues

### Database Connection Failed
- Check PostgreSQL service: `Get-Service postgresql*`
- Verify password in `.env`
- Check database exists: `psql -U postgres -l`

### Module Not Found
- Activate venv: `.\venv\Scripts\Activate.ps1`
- Reinstall: `pip install -r requirements/base.txt`

### Port Already in Use
- Change port: `python manage.py runserver 8001`
- Or kill process: `Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess`

## Files to Backup/Copy

When moving to new PC, copy:
- All source code (`*.py` files)
- `requirements/` folder
- `manage.py`
- `.env.example`
- Documentation files (`*.md`)
- `docker-compose.yml` (if using Docker)

Don't copy:
- `venv/` (recreate)
- `.env` (create new)
- `__pycache__/`
- `*.pyc`
- `db.sqlite3` (using PostgreSQL)
