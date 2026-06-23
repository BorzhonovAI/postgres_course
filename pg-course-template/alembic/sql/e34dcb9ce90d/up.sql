GRANT CREATE, USAGE ON SCHEMA inventory TO inventory_manager;
GRANT USAGE ON SCHEMA sales TO inventory_manager;
GRANT SELECT ON TABLE sales.orders TO inventory_manager;
GRANT SELECT ON TABLE sales.order_items TO inventory_manager;
GRANT UPDATE(status) ON sales.orders TO inventory_manager;
