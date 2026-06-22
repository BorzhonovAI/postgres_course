ALTER TABLE "catalog".warehouses DROP CONSTRAINT warehouses_cities_fk;
ALTER TABLE "catalog".warehouses ALTER COLUMN city_id TYPE text USING city_id::text;
ALTER TABLE "catalog".warehouses RENAME COLUMN city_id TO city;

DROP TABLE catalog.cities CASCADE;
