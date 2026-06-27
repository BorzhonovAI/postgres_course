-- ===== catalog.cities + seed data =====

CREATE TABLE "catalog".cities (
    id serial NOT NULL,
    "name" text NOT NULL,
    CONSTRAINT cities_pk PRIMARY KEY (id),
    CONSTRAINT cities_unique UNIQUE ("name")
);

ALTER ROLE app_user SET client_encoding = 'UTF8';
INSERT INTO catalog.cities (name) VALUES ('Москва');
INSERT INTO catalog.cities (name) VALUES ('Санкт-Петербург');
INSERT INTO catalog.cities (name) VALUES ('Новосибирск');
INSERT INTO catalog.cities (name) VALUES ('Екатеринбург');
INSERT INTO catalog.cities (name) VALUES ('Нижний Новгород');
INSERT INTO catalog.cities (name) VALUES ('Челябинск');
INSERT INTO catalog.cities (name) VALUES ('Самара');
INSERT INTO catalog.cities (name) VALUES ('Омск');
INSERT INTO catalog.cities (name) VALUES ('Ростов-на-Дону');
INSERT INTO catalog.cities (name) VALUES ('Уфа');
INSERT INTO catalog.cities (name) VALUES ('Красноярск');
INSERT INTO catalog.cities (name) VALUES ('Воронеж');
INSERT INTO catalog.cities (name) VALUES ('Пермь');
INSERT INTO catalog.cities (name) VALUES ('Волгоград');

-- связываем warehouses с cities
ALTER TABLE "catalog".warehouses RENAME COLUMN city TO city_id;
ALTER TABLE "catalog".warehouses ALTER COLUMN city_id TYPE int USING city_id::int;
ALTER TABLE "catalog".warehouses ADD
    CONSTRAINT warehouses_cities_fk FOREIGN KEY (city_id) REFERENCES "catalog".cities(id);

-- ===== inventory schema + core tables =====

CREATE SCHEMA inventory AUTHORIZATION app_user;

CREATE TABLE inventory.routes (
    from_city_id int NOT NULL,
    to_city_id int NOT NULL,
    duration interval minute to second NOT NULL,
    total_threshold int NOT NULL,
    CONSTRAINT routes_pk PRIMARY KEY (from_city_id,to_city_id),
    CONSTRAINT routes_total_threshold_check CHECK (total_threshold >= 0),
    CONSTRAINT routes_cities_from_fk FOREIGN KEY (from_city_id) REFERENCES "catalog".cities(id),
    CONSTRAINT routes_cities_to_fk FOREIGN KEY (to_city_id) REFERENCES "catalog".cities(id)
);

CREATE TABLE inventory.stock (
    id serial NOT NULL,
    warehouse_id int NOT NULL,
    product_id int NOT NULL,
    quantity int NOT NULL,
    CONSTRAINT stock_pk PRIMARY KEY (id),
    CONSTRAINT stock_quantity_check CHECK (quantity >= 0),
    CONSTRAINT stock_warehouses_fk FOREIGN KEY (warehouse_id) REFERENCES "catalog".warehouses(id),
    CONSTRAINT stock_products_fk FOREIGN KEY (product_id) REFERENCES "catalog".products(id)
);

CREATE TABLE inventory.deliveries (
    id serial NOT NULL,
    order_id int NOT NULL,
    status text DEFAULT 'planned' NOT NULL,
    created_at timestamp DEFAULT current_timestamp NOT NULL,
    shipped_at timestamp NULL,
    created_by_id int NOT NULL,
    CONSTRAINT deliveries_pk PRIMARY KEY (id),
    CONSTRAINT deliveries_status_check CHECK (status in ('planned', 'shipping', 'shipped')),
    CONSTRAINT deliveries_order_fk FOREIGN KEY (order_id) REFERENCES sales.orders(id),
    CONSTRAINT deliveries_created_by_fk FOREIGN KEY (created_by_id) REFERENCES auth.users(id)
);

CREATE VIEW inventory.deliveries_with_warehouse AS
SELECT d.*, o.warehouse_id
FROM inventory.deliveries d
JOIN sales.orders o ON d.order_id = o.id;

-- ===== missing inventory tables =====

CREATE TABLE inventory.reserves (
    id serial NOT NULL,
    order_id int NOT NULL,
    warehouse_id int NOT NULL,
    product_id int NOT NULL,
    quantity int NOT NULL,
    CONSTRAINT reserves_pk PRIMARY KEY (id),
    CONSTRAINT reserves_quantity_check CHECK (quantity >= 0),
    CONSTRAINT reserves_order_fk FOREIGN KEY (order_id) REFERENCES sales.orders(id),
    CONSTRAINT reserves_warehouse_fk FOREIGN KEY (warehouse_id) REFERENCES "catalog".warehouses(id),
    CONSTRAINT reserves_product_fk FOREIGN KEY (product_id) REFERENCES "catalog".products(id)
);

CREATE TABLE inventory.delivery_items (
    id serial NOT NULL,
    delivery_id int NOT NULL,
    order_id int NOT NULL,
    product_id int NOT NULL,
    quantity int NOT NULL,
    status text DEFAULT 'planned' NOT NULL,
    CONSTRAINT delivery_items_pk PRIMARY KEY (id),
    CONSTRAINT delivery_items_quantity_check CHECK (quantity >= 0),
    CONSTRAINT delivery_items_status_check CHECK (status IN ('planned', 'shipped')),
    CONSTRAINT delivery_items_delivery_fk FOREIGN KEY (delivery_id) REFERENCES inventory.deliveries(id),
    CONSTRAINT delivery_items_order_fk FOREIGN KEY (order_id) REFERENCES sales.orders(id),
    CONSTRAINT delivery_items_product_fk FOREIGN KEY (product_id) REFERENCES "catalog".products(id)
);

CREATE TABLE inventory.transfers (
    id serial NOT NULL,
    from_warehouse_id int NOT NULL,
    to_warehouse_id int NOT NULL,
    status text DEFAULT 'planned' NOT NULL,
    created_at timestamp DEFAULT current_timestamp NOT NULL,
    started_at timestamp NULL,
    arriving_at timestamp NULL,
    received_at timestamp NULL,
    total_amount numeric(12,2) DEFAULT 0 NOT NULL,
    CONSTRAINT transfers_pk PRIMARY KEY (id),
    CONSTRAINT transfers_amount_check CHECK (total_amount >= 0),
    CONSTRAINT transfers_status_check CHECK (status IN ('planned', 'shipping', 'in_transit', 'arrived', 'received')),
    CONSTRAINT transfers_from_warehouse_fk FOREIGN KEY (from_warehouse_id) REFERENCES "catalog".warehouses(id),
    CONSTRAINT transfers_to_warehouse_fk FOREIGN KEY (to_warehouse_id) REFERENCES "catalog".warehouses(id)
);

CREATE TABLE inventory.transfer_items (
    id serial NOT NULL,
    transfer_id int NOT NULL,
    product_id int NOT NULL,
    quantity int NOT NULL,
    requested_by_id int NOT NULL,
    reserve_id int NULL,
    status text DEFAULT 'planned' NOT NULL,
    CONSTRAINT transfer_items_pk PRIMARY KEY (id),
    CONSTRAINT transfer_items_quantity_check CHECK (quantity >= 0),
    CONSTRAINT transfer_items_status_check CHECK (status IN ('planned', 'shipped', 'received')),
    CONSTRAINT transfer_items_transfer_fk FOREIGN KEY (transfer_id) REFERENCES inventory.transfers(id),
    CONSTRAINT transfer_items_product_fk FOREIGN KEY (product_id) REFERENCES "catalog".products(id),
    CONSTRAINT transfer_items_requested_by_fk FOREIGN KEY (requested_by_id) REFERENCES auth.users(id),
    CONSTRAINT transfer_items_reserve_fk FOREIGN KEY (reserve_id) REFERENCES inventory.reserves(id)
);

-- ===== processing_by_id on sales.orders =====

ALTER TABLE sales.orders ADD COLUMN processing_by_id int NULL;
ALTER TABLE sales.orders ADD CONSTRAINT orders_processing_by_fk FOREIGN KEY (processing_by_id) REFERENCES auth.users(id);
