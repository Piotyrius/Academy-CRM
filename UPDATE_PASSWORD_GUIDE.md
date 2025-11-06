# Update PostgreSQL Password in .env

## Current Issue
Password authentication is failing because the password in `.env` doesn't match your PostgreSQL password.

## How to Find Your PostgreSQL Password

### Method 1: Check pgAdmin Connection
When you open pgAdmin and connect to "PostgreSQL 17", what password do you enter?
- That's the password you need to put in `.env`

### Method 2: Check pgAdmin Saved Connections
1. In pgAdmin, right-click on "PostgreSQL 17" → "Properties"
2. Go to "Connection" tab
3. You can see the password (it might be masked, but you can change it there)

### Method 3: Reset Password to "postgres"
If you want to use "postgres" as password:
1. In pgAdmin, right-click on "PostgreSQL 17" → "Properties"
2. Go to "Connection" tab
3. Change password to "postgres"
4. Update `.env`: `DB_PASSWORD=postgres`

## Update .env File

Edit `.env` and change:
```
DB_PASSWORD=postgres
```

To your actual password:
```
DB_PASSWORD=your_actual_password_here
```

## After Updating Password

1. Test connection:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python test_postgres_connection.py
   ```

2. If successful, run migrations:
   ```powershell
   python manage.py migrate
   ```

3. Create superuser:
   ```powershell
   python manage.py createsuperuser
   ```
