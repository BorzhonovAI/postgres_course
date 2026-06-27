REVOKE CREATE, USAGE ON SCHEMA inventory FROM inventory_manager;
REVOKE ALL ON ALL TABLES IN SCHEMA inventory FROM inventory_manager;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA inventory FROM inventory_manager;

REVOKE USAGE ON SCHEMA sales FROM inventory_manager;
REVOKE SELECT ON TABLE sales.orders FROM inventory_manager;
REVOKE SELECT ON TABLE sales.order_items FROM inventory_manager;
REVOKE UPDATE (status) ON sales.orders FROM inventory_manager;

REVOKE USAGE ON SCHEMA catalog FROM inventory_manager;
REVOKE SELECT ON ALL TABLES IN SCHEMA catalog FROM inventory_manager;

REVOKE USAGE ON SCHEMA auth FROM inventory_manager;
REVOKE SELECT ON ALL TABLES IN SCHEMA auth FROM inventory_manager;