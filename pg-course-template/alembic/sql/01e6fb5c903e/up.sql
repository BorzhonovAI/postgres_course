ALTER TABLE sales.orders ADD created_by_id int NULL;

UPDATE sales.orders SET created_by_id =
(SELECT id FROM auth.users where role = 'sales_manager' ORDER BY id LIMIT 1);

ALTER TABLE sales.orders ALTER COLUMN created_by_id SET NOT NULL;

ALTER TABLE sales.orders ADD CONSTRAINT orders_created_by_fkey
FOREIGN KEY (created_by_id) REFERENCES auth.users (id);