# Create Database in pgAdmin

## Step-by-Step Instructions

Based on your pgAdmin screenshot, you have PostgreSQL 16, 17, and invitationrender servers.

### Steps:

1. **Choose a PostgreSQL Server**
   - Right-click on any of your PostgreSQL servers (PostgreSQL 16, 17, or invitationrender)
   - Or use the one you normally connect to

2. **Create Database**
   - Right-click on "Databases" (under your chosen server)
   - Select "Create" → "Database..."

3. **Database Properties**
   - **General Tab**:
     - **Database**: `academy_crm`
     - **Owner**: `postgres` (default)
     - **Comment**: (optional) "Academy CRM Database"
   
   - **Definition Tab**:
     - **Encoding**: `UTF8` (default)
     - **Template**: `template0` (recommended)
     - **Collation**: `en_US.UTF-8` or `C` (default)
     - **Character Type**: `en_US.UTF-8` or `C` (default)
   
   - **Connection Limit**: `-1` (unlimited) or leave default

4. **Click "Save"**

5. **Verify**
   - The database `academy_crm` should now appear under "Databases" in your server

## Alternative: Using SQL Query

1. Right-click on your PostgreSQL server → "Query Tool"
2. Paste this SQL:
   ```sql
   CREATE DATABASE academy_crm;
   ```
3. Click the "Execute" button (or press F5)
4. You should see: "Query returned successfully"

## After Creating Database

1. Update `.env` with your PostgreSQL password (if not already done)
2. Test connection:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python test_postgres_connection.py
   ```
3. Run migrations:
   ```powershell
   python manage.py migrate
   ```

## Troubleshooting

**Database name already exists?**
- Use a different name or drop the existing one:
  ```sql
  DROP DATABASE IF EXISTS academy_crm;
  CREATE DATABASE academy_crm;
  ```

**Permission denied?**
- Make sure you're using the `postgres` user or a user with CREATE DATABASE privileges
