CREATE DATABASE inventorydb;
CREATE ROLE app_user WITH LOGIN PASSWORD 'gfhjkm';
CREATE ROLE catalog_manager WITH LOGIN PASSWORD 'catalog';
CREATE ROLE sales_manager WITH LOGIN PASSWORD 'sales';
CREATE ROLE supervisor WITH LOGIN PASSWORD 'password';
GRANT CREATE ON DATABASE inventorydb TO app_user;

