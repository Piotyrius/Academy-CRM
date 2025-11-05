# PostgreSQL Setup Steps

Since you already have PostgreSQL and pgAdmin running, follow these steps:

## Step 1: Create Database

### Option A: Using pgAdmin (Easiest)

1. Open pgAdmin
2. Connect to your PostgreSQL server (usually "PostgreSQL 15" or similar)
3. Right-click on "Databases" → "Create" → "Database"
4. Name: `academy_crm`
5. Owner: `postgres` (default)
6. Click "Save"

### Option B: Using SQL Query in pgAdmin

1. Open pgAdmin
2. Right-click on your PostgreSQL server → "Query Tool"
3. Run this SQL:
   ```sql
   CREATE DATABASE academy_crm;
   ```

### Option C: Using Command Line

```powershell
psql -U postgres
CREATE DATABASE academy_crm;
\q
```

## Step 2: Update .env File

Edit the `.env` file in your project root and set:

```
DB_NAME=academy_crm
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here
DB_HOST=localhost
DB_PORT=5432
```

**Note**: If you don't know your postgres password, you can reset it in pgAdmin or use Windows authentication.

## Step 3: Test Connection

```powershell
# Remove SQLite if set
$env:USE_SQLITE = $null

# Test connection
python manage.py dbshell
# Should connect to PostgreSQL
# Type \q to exit
```

## Step 4: Run Migrations

```powershell
python manage.py migrate
```

## Step 5: Create Superuser

```powershell
python manage.py createsuperuser
```

## Verify Everything Works

```powershell
# Start server
python manage.py runserver

# Visit: http://localhost:8000/api/docs/
# Should see Swagger UI
```

## Troubleshooting

**Connection refused?**
- Check PostgreSQL service is running: `Get-Service | Where-Object {$_.Name -like "*postgres*"}`
- Verify port 5432 is correct

**Password authentication failed?**
- Check password in `.env` matches your postgres user password
- Or use Windows authentication (if configured)

**Database doesn't exist?**
- Create it in pgAdmin (see Step 1)
