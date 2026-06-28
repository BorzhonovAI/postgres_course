CREATE SCHEMA IF NOT EXISTS auth AUTHORIZATION app_user;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS auth.users (
    id SERIAL PRIMARY KEY,
    username text NOT NULL,
    "password" text NOT NULL,
    "role" text NOT NULL,
    CONSTRAINT role_check CHECK (role in ('catalog_manager', 'sales_manager', 'inventory_manager', 'worker'))
);

-- Insert seed users only if they don't already exist
INSERT INTO auth.users (username, password, role)
SELECT 'sal', crypt('sales', gen_salt('bf')), 'sales_manager'
WHERE NOT EXISTS (SELECT 1 FROM auth.users WHERE username = 'sal');
INSERT INTO auth.users (username, password, role)
SELECT 'cat', crypt('catalog', gen_salt('bf')), 'catalog_manager'
WHERE NOT EXISTS (SELECT 1 FROM auth.users WHERE username = 'cat');
INSERT INTO auth.users (username, password, role)
SELECT 'inv', crypt('inventory', gen_salt('bf')), 'inventory_manager'
WHERE NOT EXISTS (SELECT 1 FROM auth.users WHERE username = 'inv');
INSERT INTO auth.users (username, password, role)
SELECT 'wrk', crypt('worker', gen_salt('bf')), 'worker'
WHERE NOT EXISTS (SELECT 1 FROM auth.users WHERE username = 'wrk');
