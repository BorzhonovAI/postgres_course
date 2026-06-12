ALTER TABLE sales.order_items DROP CONSTRAINT order_items_order_id_fkey;
ALTER TABLE sales.order_items ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES sales.orders(id) ON DELETE CASCADE;

