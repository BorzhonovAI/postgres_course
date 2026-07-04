CREATE SCHEMA sales;
create table sales.orders (
        id serial PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'unpublished',
        total_amount decimal(10, 2) NOT NULL DEFAULT 0,
        created_at timestamp NOT NULL DEFAULT current_timestamp,
        warehouse_id integer NOT NULL REFERENCES catalog.warehouses (id),
        CONSTRAINT status_check
        CHECK( status in ('unpublished', 'new', 'processing', 'pending', 'packing', 'shipped'))
);
create table sales.order_items (
        order_id int NOT NULL REFERENCES sales.orders (id) ON DELETE CASCADE,
        product_id int NOT NULL REFERENCES catalog.products (id),
        quantity int NOT NULL,
        price decimal(10, 2) NOT NULL,
	PRIMARY KEY (order_id, product_id),
        CONSTRAINT price_check CHECK(price > 0),
        CONSTRAINT quantity_check CHECK(quantity > 0)
);
