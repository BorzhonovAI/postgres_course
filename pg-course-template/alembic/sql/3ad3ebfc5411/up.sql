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
	status text DEFAULT 'planned' NOT NULL,
	created_at timestamp DEFAULT current_timestamp NOT NULL,
	shipped_at timestamp NULL,
	created_by_id int NOT NULL,
	CONSTRAINT deliveries_pk PRIMARY KEY (id),
	CONSTRAINT deliveries_status_check CHECK (status in ('planned', 'shipping', 'shipped')),
	CONSTRAINT deliveries_created_by_fk FOREIGN KEY (created_by_id) REFERENCES auth.users(id)
);

-- вероятно поле deliveries.created_by_id тоже можно было бы добавить через представление
-- это представление добавлено на случай если worker хотел бы видеть список доставок только со своего склада
CREATE VIEW inventory.deliveries_with_warehouse AS
SELECT d.*, o.warehouse_id
FROM inventory.deliveries d
JOIN sales.orders o ON d.order_id = o.id;
