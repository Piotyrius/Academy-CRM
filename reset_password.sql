-- Reset PostgreSQL password for postgres user
-- Run this in pgAdmin Query Tool

-- Step 1: Connect to PostgreSQL 17 server
-- Step 2: Open Query Tool (right-click server -> Query Tool)
-- Step 3: Run this SQL

-- Reset password to 'postgres' (change if you prefer a different password)
ALTER USER postgres WITH PASSWORD 'postgres';

-- Verify the change
SELECT usename FROM pg_user WHERE usename = 'postgres';

-- After running this, update your .env file:
-- DB_PASSWORD=postgres
