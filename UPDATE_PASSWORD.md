# Update PostgreSQL Password in .env

## Issue
Password authentication failed - the password in `.env` doesn't match your PostgreSQL password.

## Solution

### Step 1: Find Your PostgreSQL Password

**Option A: Check pgAdmin**
1. In pgAdmin, when you connect to your server, what password do you use?
2. That's your PostgreSQL password for the `postgres` user

**Option B: Reset Password in pgAdmin**
1. Right-click on your PostgreSQL server → "Properties"
2. Go to "Connection" tab
3. You can see/change the password there

### Step 2: Update .env File

Edit `.env` file and change:
```
DB_PASSWORD=postgres
```

To your actual PostgreSQL password:
```
DB_PASSWORD=your_actual_password_here
```

### Step 3: Test Again

```powershell
.\venv\Scripts\Activate.ps1
python test_postgres_connection.py
```

### Step 4: If Successful, Run Migrations

```powershell
python manage.py migrate
```

## Alternative: Reset PostgreSQL Password

If you want to use "postgres" as password:

1. In pgAdmin, right-click on PostgreSQL server → "Properties"
2. Go to "Connection" tab
3. Change password to "postgres"
4. Update `.env` file: `DB_PASSWORD=postgres`

## Quick Test

After updating password, test with:
```powershell
.\venv\Scripts\Activate.ps1
python manage.py dbshell
# Should connect successfully
# Type \q to exit
```
