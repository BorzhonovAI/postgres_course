ALTER TABLE sales.orders ADD CONSTRAINT total_amount_check CHECK(total_amount > 0)
