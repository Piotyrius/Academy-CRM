# Quick Fix: Update PostgreSQL Password

## The Problem
Password authentication is failing because `.env` has the wrong password.

## The Solution

### Step 1: Find Your Password
When you connect to "PostgreSQL 17" in pgAdmin, what password do you enter?
- That's the password you need!

### Step 2: Update .env File

1. Open `.env` file in your project root
2. Find this line:
   ```
   DB_PASSWORD=postgres
   ```
3. Replace `postgres` with your actual password:
   ```
   DB_PASSWORD=your_actual_password_here
   ```
4. Save the file

### Step 3: Test Connection

```powershell
.\venv\Scripts\Activate.ps1
python test_postgres_connection.py
```

If you see ✅ "PostgreSQL Connection Successful!" - you're done!

### Step 4: Run Migrations

```powershell
python manage.py migrate
```

## If You Don't Know Your Password

**Option 1: Reset in pgAdmin**
1. Right-click "PostgreSQL 17" → "Properties" → "Connection"
2. Change password to something simple like `postgres`
3. Update `.env`: `DB_PASSWORD=postgres`

**Option 2: Use psql command line**
```powershell
# Connect to PostgreSQL (it will ask for password)
psql -U postgres
# Then change password:
ALTER USER postgres PASSWORD 'newpassword';
```

**Option 3: Check Windows Authentication**
If you're using Windows authentication, you might not need a password. But Django still needs one, so set a password for the postgres user.
