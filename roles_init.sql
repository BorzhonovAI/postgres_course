DO
$$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'catalog_manager') THEN
    CREATE ROLE catalog_manager WITH LOGIN PASSWORD 'catalog';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sales_manager') THEN
    CREATE ROLE sales_manager WITH LOGIN PASSWORD 'sales';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'supervisor') THEN
    CREATE ROLE supervisor WITH LOGIN PASSWORD 'password';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'inventory_manager') THEN
    CREATE ROLE inventory_manager WITH LOGIN PASSWORD 'inventory';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'worker') THEN
    CREATE ROLE worker WITH LOGIN PASSWORD 'worker';
  END IF;
END
$$;
