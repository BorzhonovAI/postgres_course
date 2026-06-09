CREATE SCHEMA sales AUTHORIZATION app_user;
GRANT CREATE ON SCHEMA sales TO app_user;
set search_path to catalog, sales;
create table sales.orders (
        id serial PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'unpublished',
        total_amount integer NOT NULL,
        created_at timestamp NOT NULL,
        warehouse_id integer NOT NULL REFERENCES catalog.warehouses (id),
        CONSTRAINT status_check
        CHECK( status in ('unpublished', 'new', 'processing', 'new', 'pending', 'packing', 'shipped')),
        CONSTRAINT total_amount_check CHECK(total_amount > 0)
);
create table sales.order_items (
        order_id int NOT NULL REFERENCES sales.orders (id),
        product_id int NOT NULL REFERENCES catalog.products (id),
        quantity int NOT NULL,
        price integer NOT NULL,
        CONSTRAINT price_check CHECK(price > 0),
        CONSTRAINT quantity_check CHECK(quantity > 0)
);