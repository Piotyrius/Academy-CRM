# Install PostgreSQL for Local Development

## Quick Answer

**Yes, you can:**
- ✅ Use PostgreSQL locally for development (no Docker needed)
- ✅ Use Docker for deployment later (on server)
- ✅ PostgreSQL alone is enough for development phase

## Installation Methods

### Method 1: Official Installer (Easiest)

1. **Download PostgreSQL**:
   - Go to: https://www.postgresql.org/download/windows/
   - Click "Download the installer"
   - Choose version 15 or 16 (recommended)
   - Download the installer (e.g., `postgresql-15.7-1-windows-x64.exe`)

2. **Run Installer**:
   - Install with default settings
   - **Important**: Remember the password you set for `postgres` user
   - Port: 5432 (default)
   - Components: Install everything (including pgAdmin if you want)

3. **Verify Installation**:
   ```powershell
   # Check if psql is available
   psql --version
   
   # Should show version number
   ```

### Method 2: Using Winget (Windows 11/10)

```powershell
winget install PostgreSQL.PostgreSQL
```

After installation, you'll need to:
- Set password for postgres user
- Start the service

### Method 3: Using Chocolatey (if installed)

```powershell
choco install postgresql
```

## After Installation

### 1. Start PostgreSQL Service

```powershell
# Check service status
Get-Service | Where-Object {$_.Name -like "*postgres*"}

# Start if stopped (replace with actual service name)
Start-Service postgresql-x64-15
```

### 2. Create Database

```powershell
# Connect (it will ask for password)
psql -U postgres

# In psql:
CREATE DATABASE academy_crm;
\q
```

### 3. Update .env File

Edit `.env` file:
```
DB_NAME=academy_crm
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
```

### 4. Test Connection

```powershell
# Remove SQLite if set
$env:USE_SQLITE = $null

# Test connection
python manage.py migrate
```

## Docker for Deployment (Later)

**Yes, you can use Docker for deployment without Docker Desktop:**

- **Local Development**: PostgreSQL installed on your machine
- **Server/Production**: Docker Compose (just install Docker on the server, no Docker Desktop needed)

The `docker-compose.yml` file works on any Linux server with Docker installed (no Docker Desktop required).

## Summary

✅ **For Development**: Install PostgreSQL locally (no Docker needed)
✅ **For Deployment**: Use Docker Compose on server (Docker Desktop not required)
✅ **PostgreSQL alone is sufficient** for development phase

## Next Steps

1. Install PostgreSQL (Method 1 recommended)
2. Create database: `CREATE DATABASE academy_crm;`
3. Update `.env` with password
4. Run: `python manage.py migrate`
5. You're ready to develop!

No Docker Desktop needed for local development! 🎉
