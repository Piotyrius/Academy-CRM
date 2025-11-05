# Setup Database with pgAdmin (You Already Have It!)

## Step 1: Create Database in pgAdmin

1. **Open pgAdmin** (already running ✅)

2. **Connect to PostgreSQL Server**:
   - Expand "Servers" in the left panel
   - Click on your PostgreSQL server (usually "PostgreSQL 15" or similar)
   - Enter your PostgreSQL password if prompted

3. **Create Database**:
   - Right-click on "Databases"
   - Select "Create" → "Database..."
   - Database name: `academy_crm`
   - Owner: `postgres` (or your PostgreSQL user)
   - Click "Save"

**OR use SQL Query Tool**:
   - Right-click on your server → "Query Tool"
   - Paste this SQL:
   ```sql
   CREATE DATABASE academy_crm;
   ```
   - Click "Execute" (F5)

## Step 2: Update .env File

Open `.env` file and set your PostgreSQL credentials:

```
DB_NAME=academy_crm
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here
DB_HOST=localhost
DB_PORT=5432
```

**Note**: Replace `your_postgres_password_here` with your actual PostgreSQL password.

## Step 3: Test Connection

```powershell
# Make sure SQLite is not being used
$env:USE_SQLITE = $null

# Test connection
python manage.py check --database default
```

## Step 4: Run Migrations

```powershell
python manage.py migrate
```

## Step 5: Create Superuser

```powershell
python manage.py createsuperuser
# Use: admin@academy.edu.ge / admin
```

## Verify Everything Works

```powershell
# Start server
python manage.py runserver

# Should connect to PostgreSQL automatically
# Check logs for any database connection errors
```

## Troubleshooting

**Connection refused?**
- Check PostgreSQL service is running: `Get-Service postgresql*`
- Verify port 5432 is correct in `.env`
- Check firewall isn't blocking port 5432

**Authentication failed?**
- Verify password in `.env` matches your PostgreSQL password
- Try connecting in pgAdmin first to verify credentials

**Database doesn't exist?**
- Create it in pgAdmin (see Step 1)
- Or use SQL: `CREATE DATABASE academy_crm;`
