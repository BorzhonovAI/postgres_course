ALTER TABLE catalog.products ADD CONSTRAINT products_category_id_fkey
FOREIGN KEY (category_id) REFERENCES catalog.product_categories (id);
