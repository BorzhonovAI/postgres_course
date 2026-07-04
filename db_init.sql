-- Create database if it does not exist
SELECT 'CREATE DATABASE inventorydb'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'inventorydb')\gexec

-- Create app_user role if it does not exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH CREATEROLE LOGIN PASSWORD 'gfhjkm';
    END IF;
END$$;

GRANT CREATE ON DATABASE inventorydb TO app_user;
