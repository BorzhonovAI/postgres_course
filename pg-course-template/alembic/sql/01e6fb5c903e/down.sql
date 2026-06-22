ALTER TABLE sales.orders DROP CONSTRAINT orders_created_by_fkey;
ALTER TABLE sales.orders DROP COLUMN created_by_id;
