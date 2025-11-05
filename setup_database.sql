-- SQL script to create Academy CRM database
-- Run this in pgAdmin Query Tool or psql

-- Create database (if it doesn't exist)
CREATE DATABASE academy_crm
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- Verify database was created
\c academy_crm

-- Show connection info
SELECT current_database(), current_user;

-- You should see: academy_crm | postgres