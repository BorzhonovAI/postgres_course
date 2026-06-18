ALTER DEFAULT PRIVILEGES IN SCHEMA "catalog" GRANT SELECT ON TABLES TO PUBLIC;

GRANT ALL ON SCHEMA "catalog" TO catalog_manager;
GRANT ALL ON ALL TABLES IN SCHEMA "catalog" TO catalog_manager;
GRANT ALL ON ALL SEQUENCES IN SCHEMA "catalog" TO catalog_manager;
ALTER DEFAULT PRIVILEGES IN SCHEMA "catalog" GRANT ALL ON TABLES TO catalog_manager;

GRANT ALL ON SCHEMA sales TO sales_manager;
GRANT ALL ON ALL TABLES IN SCHEMA sales TO sales_manager;
GRANT ALL ON ALL SEQUENCES IN SCHEMA sales TO sales_manager;
ALTER DEFAULT PRIVILEGES IN SCHEMA sales GRANT ALL ON TABLES TO sales_manager;
GRANT USAGE ON SCHEMA "catalog" TO sales_manager;
GRANT SELECT ON ALL TABLES in schema "catalog" TO sales_manager;
ALTER DEFAULT PRIVILEGES IN SCHEMA "catalog" GRANT SELECT ON TABLES TO sales_manager;

GRANT sales_manager TO supervisor;
GRANT catalog_manager TO supervisor;

GRANT USAGE ON SCHEMA auth TO sales_manager, catalog_manager;
GRANT SELECT ON ALL TABLES in schema auth TO sales_manager, catalog_manager;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT SELECT ON TABLES TO sales_manager, catalog_manager;
