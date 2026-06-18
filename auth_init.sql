CREATE SCHEMA auth AUTHORIZATION app_user;
CREATE TABLE auth.users (
	username text NOT NULL,
	"password" text NOT NULL,
	"role" text NOT NULL,
	CONSTRAINT users_pk PRIMARY KEY (username),
	CONSTRAINT role_check CHECK (role in ('catalog_manager', 'sales_manager'))
);
CREATE EXTENSION IF NOT EXISTS pgcrypto;

--для простоты пароли пользователей будут совпадать с паролями ролей
insert into auth.users (username, password, role) VALUES
('sal', crypt('sales', gen_salt('bf')), 'sales_manager');
insert into auth.users (username, password, role) VALUES
('cat', crypt('catalog', gen_salt('bf')), 'catalog_manager');

