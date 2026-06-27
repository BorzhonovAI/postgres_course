-- Таблица резервирования товаров для заказов
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

-- Позиции в накладной на доставку заказа покупателю
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

-- Накладные на перемещение товаров между складами
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

-- Позиции в накладной на перемещение
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
