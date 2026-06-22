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

-- настраиваем связь с таблицей warehouses
ALTER TABLE "catalog".warehouses RENAME COLUMN city TO city_id;
ALTER TABLE "catalog".warehouses ALTER COLUMN city_id TYPE int USING city_id::int;
ALTER TABLE "catalog".warehouses ADD
CONSTRAINT warehouses_cities_fk FOREIGN KEY (city_id) REFERENCES "catalog".cities(id);


