ALTER TABLE sales.orders ADD COLUMN processing_by_id int NULL;
ALTER TABLE sales.orders ADD CONSTRAINT orders_processing_by_fk FOREIGN KEY (processing_by_id) REFERENCES auth.users(id);
