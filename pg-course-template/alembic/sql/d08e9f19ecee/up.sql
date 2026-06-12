ALTER TABLE "catalog".products DROP CONSTRAINT products_category_id_fkey;
ALTER TABLE "catalog".products ADD CONSTRAINT products_category_id_fkey FOREIGN KEY (category_id) REFERENCES "catalog".product_categories(id) ON DELETE CASCADE;

