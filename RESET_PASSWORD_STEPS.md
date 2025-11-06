# Reset PostgreSQL Password

Since the password field is masked in pgAdmin, let's reset it to a known value.

## Method 1: Reset via pgAdmin Query Tool (Recommended)

### Steps:

1. **In pgAdmin, right-click on "PostgreSQL 17"** → **"Query Tool"**

2. **Connect** (if prompted, use whatever password currently works - or if you can't connect, we'll use Method 2)

3. **Paste and run this SQL:**
   ```sql
   ALTER USER postgres WITH PASSWORD 'postgres';
   ```

4. **Click "Execute"** (or press F5)

5. **Update your `.env` file:**
   - Open `.env`
   - Set: `DB_PASSWORD=postgres`
   - Save

6. **Test connection:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python test_postgres_connection.py
   ```

## Method 2: If You Can't Connect to Query Tool

If pgAdmin requires a password you don't know:

### Option A: Use Windows Authentication

1. **Check if you can connect without password:**
   - Try connecting to PostgreSQL 17 in pgAdmin
   - If it connects without asking for password, you might be using Windows authentication

2. **Set password for postgres user:**
   - Once connected (via Windows auth), open Query Tool
   - Run: `ALTER USER postgres WITH PASSWORD 'postgres';`

### Option B: Reset via Command Line (if psql is in PATH)

1. **Find PostgreSQL bin directory:**
   - Usually: `C:\Program Files\PostgreSQL\17\bin\`
   
2. **Open PowerShell as Administrator**

3. **Run:**
   ```powershell
   cd "C:\Program Files\PostgreSQL\17\bin"
   .\psql.exe -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"
   ```
   (It might prompt for current password - if you don't know it, use Method C)

### Option C: Reset via pg_hba.conf (Last Resort)

1. **Find pg_hba.conf:**
   - Usually: `C:\Program Files\PostgreSQL\17\data\pg_hba.conf`

2. **Temporarily change authentication:**
   - Find line: `host    all             all             127.0.0.1/32            scram-sha-256`
   - Change to: `host    all             all             127.0.0.1/32            trust`
   - Save file

3. **Restart PostgreSQL service:**
   ```powershell
   Restart-Service postgresql-x64-17
   ```

4. **Connect without password:**
   - Now connect in pgAdmin (no password needed)
   - Run: `ALTER USER postgres WITH PASSWORD 'postgres';`
   - Revert pg_hba.conf back to `scram-sha-256`
   - Restart service again

## Quick Test After Reset

Once password is set to 'postgres':

1. Update `.env`: `DB_PASSWORD=postgres`
2. Test: `python test_postgres_connection.py`
3. Run migrations: `python manage.py migrate`
