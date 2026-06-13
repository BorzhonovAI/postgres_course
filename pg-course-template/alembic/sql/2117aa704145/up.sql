CREATE SCHEMA sales AUTHORIZATION app_user;
GRANT CREATE ON SCHEMA sales TO app_user;
set search_path to catalog, sales;
create table sales.orders (
        id serial PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'unpublished',
        total_amount integer NOT NULL DEFAULT 0,
        created_at timestamp NOT NULL DEFAULT current_timestamp,
        warehouse_id integer NOT NULL REFERENCES catalog.warehouses (id),
        CONSTRAINT status_check
        CHECK( status in ('unpublished', 'new', 'processing', 'new', 'pending', 'packing', 'shipped'))
);
create table sales.order_items (
        order_id int NOT NULL REFERENCES sales.orders (id) ON DELETE CASCADE,
        product_id int NOT NULL REFERENCES catalog.products (id),
        quantity int NOT NULL,
        price integer NOT NULL,
	PRIMARY KEY (order_id, product_id),
        CONSTRAINT price_check CHECK(price > 0),
        CONSTRAINT quantity_check CHECK(quantity > 0)
);
