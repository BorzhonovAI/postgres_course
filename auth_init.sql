CREATE SCHEMA auth AUTHORIZATION app_user;
CREATE TABLE auth.users (
	username text NOT NULL,
	"password" text NOT NULL,
	"role" text NOT NULL,
	CONSTRAINT users_pk PRIMARY KEY (username),
	CONSTRAINT role_check CHECK (role in ('catalog_manager', 'sales_manager'))
);
CREATE EXTENSION IF NOT EXISTS pgcrypto;

