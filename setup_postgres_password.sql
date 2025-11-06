-- Set password for postgres user
-- Run this in pgAdmin Query Tool (right-click PostgreSQL 17 -> Query Tool)

-- Set password for postgres user
ALTER USER postgres WITH PASSWORD 'postgres';

-- Verify it worked
SELECT usename FROM pg_user WHERE usename = 'postgres';

-- After this, update .env file: DB_PASSWORD=postgres
