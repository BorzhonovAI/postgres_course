REVOKE CREATE, USAGE ON SCHEMA inventory FROM inventory_manager;
REVOKE USAGE ON SCHEMA sales FROM inventory_manager;
REVOKE SELECT ON TABLE sales.orders FROM inventory_manager;
REVOKE SELECT ON TABLE sales.order_items FROM inventory_manager;
REVOKE UPDATE (status) ON sales.orders FROM inventory_manager;