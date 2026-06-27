GRANT USAGE ON SCHEMA inventory TO worker;

-- Reading all inventory tables
GRANT SELECT ON ALL TABLES IN SCHEMA inventory TO worker;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA inventory GRANT SELECT ON TABLES TO worker;

-- All rights on stock table
GRANT ALL ON TABLE inventory.stock TO worker;

-- Update reserves
GRANT UPDATE ON TABLE inventory.reserves TO worker;

-- Update statuses and dates in deliveries
GRANT UPDATE (status, shipped_at) ON TABLE inventory.deliveries TO worker;

-- Update statuses in delivery_items
GRANT UPDATE (status) ON TABLE inventory.delivery_items TO worker;

-- Update statuses and dates in transfers
GRANT UPDATE (status, started_at, arriving_at, received_at, total_amount) ON TABLE inventory.transfers TO worker;

-- Update statuses in transfer_items
GRANT UPDATE (status) ON TABLE inventory.transfer_items TO worker;

-- Read access to catalog for city/warehouse names
GRANT USAGE ON SCHEMA catalog TO worker;
GRANT SELECT ON ALL TABLES IN SCHEMA catalog TO worker;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA "catalog" GRANT SELECT ON TABLES TO worker;
