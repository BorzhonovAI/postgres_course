GRANT CREATE, USAGE ON SCHEMA inventory TO inventory_manager;
GRANT ALL ON ALL TABLES IN SCHEMA inventory TO inventory_manager;
GRANT ALL ON ALL SEQUENCES IN SCHEMA inventory TO inventory_manager;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA inventory GRANT ALL ON TABLES TO inventory_manager;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA inventory GRANT ALL ON SEQUENCES TO inventory_manager;

GRANT USAGE ON SCHEMA sales TO inventory_manager;
GRANT SELECT ON TABLE sales.orders TO inventory_manager;
GRANT SELECT ON TABLE sales.order_items TO inventory_manager;
GRANT UPDATE(status) ON sales.orders TO inventory_manager;

GRANT USAGE ON SCHEMA catalog TO inventory_manager;
GRANT SELECT ON ALL TABLES IN SCHEMA catalog TO inventory_manager;

GRANT USAGE ON SCHEMA auth TO inventory_manager;
GRANT SELECT ON ALL TABLES IN SCHEMA auth TO inventory_manager;
