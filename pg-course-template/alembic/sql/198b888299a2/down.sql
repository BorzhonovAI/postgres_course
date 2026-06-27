REVOKE USAGE ON SCHEMA inventory FROM worker;

REVOKE SELECT ON ALL TABLES IN SCHEMA inventory FROM worker;

REVOKE ALL ON TABLE inventory.stock FROM worker;

REVOKE UPDATE ON TABLE inventory.reserves FROM worker;

REVOKE UPDATE (status, shipped_at) ON TABLE inventory.deliveries FROM worker;

REVOKE UPDATE (status) ON TABLE inventory.delivery_items FROM worker;

REVOKE UPDATE (status, started_at, arriving_at, received_at, total_amount) ON TABLE inventory.transfers FROM worker;

REVOKE UPDATE (status) ON TABLE inventory.transfer_items FROM worker;

REVOKE USAGE ON SCHEMA catalog FROM worker;
REVOKE SELECT ON ALL TABLES IN SCHEMA catalog FROM worker;
