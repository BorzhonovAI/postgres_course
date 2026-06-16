CREATE DATABASE inventorydb;
CREATE ROLE app_user WITH LOGIN PASSWORD 'gfhjkm';
GRANT CREATE ON DATABASE inventorydb TO app_user;

