-- undo: processing_by_id on sales.orders

ALTER TABLE sales.orders DROP CONSTRAINT orders_processing_by_fk;
ALTER TABLE sales.orders DROP COLUMN processing_by_id;

-- undo: missing inventory tables

DROP TABLE inventory.transfer_items;
DROP TABLE inventory.transfers;
DROP TABLE inventory.delivery_items;
DROP TABLE inventory.reserves;

-- undo: inventory schema + core tables

DROP SCHEMA inventory CASCADE;

-- undo: catalog.cities + warehouses linkage

ALTER TABLE "catalog".warehouses DROP CONSTRAINT warehouses_cities_fk;
ALTER TABLE "catalog".warehouses ALTER COLUMN city_id TYPE text USING city_id::text;
ALTER TABLE "catalog".warehouses RENAME COLUMN city_id TO city;

DROP TABLE catalog.cities CASCADE;
