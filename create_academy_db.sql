-- Create Academy CRM Database
-- Run this in pgAdmin Query Tool

-- Connect to your PostgreSQL server first (PostgreSQL 16, 17, or invitationrender)
-- Then run this script

-- Create database
CREATE DATABASE academy_crm
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- Verify database was created
SELECT datname FROM pg_database WHERE datname = 'academy_crm';

-- You should see: academy_crm
