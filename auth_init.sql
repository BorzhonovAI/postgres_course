CREATE SCHEMA auth AUTHORIZATION app_user;
CREATE TABLE auth.users (
    id SERIAL PRIMARY KEY,
	username text NOT NULL,
	"password" text NOT NULL,
	"role" text NOT NULL,
	CONSTRAINT role_check CHECK (role in ('catalog_manager', 'sales_manager', 'inventory_manager', 'worker'))
);
CREATE EXTENSION IF NOT EXISTS pgcrypto;

--для простоты пароли пользователей будут совпадать с паролями ролей
INSERT INTO auth.users (username, password, role) VALUES
('sal', crypt('sales', gen_salt('bf')), 'sales_manager');
INSERT INTO auth.users (username, password, role) VALUES
('cat', crypt('catalog', gen_salt('bf')), 'catalog_manager');
INSERT INTO auth.users (username, password, role) VALUES
('inv', crypt('inventory', gen_salt('bf')), 'inventory_manager');
INSERT INTO auth.users (username, password, role) VALUES
('wrk', crypt('worker', gen_salt('bf')), 'worker');

