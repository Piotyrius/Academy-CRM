# Quick Setup Steps (You Have PostgreSQL + pgAdmin)

## ✅ Step 1: Create Database in pgAdmin

1. In **pgAdmin** (already open):
   - Expand "Servers" → Your PostgreSQL server
   - Right-click on **"Databases"** → **Create** → **Database...**
   - **Name**: `academy_crm`
   - **Owner**: `postgres`
   - Click **"Save"**

**OR use Query Tool**:
   - Right-click server → **Query Tool**
   - Run: `CREATE DATABASE academy_crm;`

## ✅ Step 2: Verify .env File

Your `.env` already has:
```
DB_NAME=academy_crm
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

**If your PostgreSQL password is different**, update `DB_PASSWORD` in `.env`

## ✅ Step 3: Test Connection & Run Migrations

```powershell
# Remove SQLite if it was set
$env:USE_SQLITE = $null

# Test connection
python manage.py check --database default

# If successful, run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## ✅ Step 4: Start Server

```powershell
python manage.py runserver
```

You should now be using PostgreSQL! 🎉
