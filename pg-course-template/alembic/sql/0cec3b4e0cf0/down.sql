-- undo: processing_by on sales.orders

ALTER TABLE sales.orders DROP CONSTRAINT orders_processing_by_fk;
ALTER TABLE sales.orders DROP COLUMN processing_by;

-- undo: partial unique indexes

DROP INDEX IF EXISTS transfer_items_uniq_not_null_reserve;
DROP INDEX IF EXISTS transfer_items_uniq_null_reserve;
DROP INDEX IF EXISTS transfers_single_planned_per_route;

-- undo: missing inventory tables

DROP TABLE inventory.transfer_items;
DROP TABLE inventory.transfers;
DROP TABLE inventory.delivery_items;
DROP TABLE inventory.reserves;

-- undo: inventory schema + core tables

DROP SCHEMA inventory CASCADE;

-- undo: catalog.cities + warehouses linkage

ALTER TABLE "catalog".warehouses DROP CONSTRAINT warehouses_cities_fk;

-- восстановить текстовый город из cities (пока таблица ещё существует)
ALTER TABLE "catalog".warehouses ADD COLUMN city text;
ALTER TABLE "catalog".warehouses ALTER COLUMN city_id DROP NOT NULL;
UPDATE "catalog".warehouses w
SET city = c."name"
FROM "catalog".cities c
WHERE c.id = w.city_id;
ALTER TABLE "catalog".warehouses DROP COLUMN city_id;

DROP TABLE catalog.cities CASCADE;
