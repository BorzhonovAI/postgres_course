#!/bin/bash

cd /home/anatoly/work/postgres_db
docker compose up -d
docker cp /home/anatoly/work/projects/postgres_course/db_init.sql db:/tmp/
docker cp /home/anatoly/work/projects/postgres_course/roles_init.sql db:/tmp/
docker cp /home/anatoly/work/projects/postgres_course/alembic_init.sql db:/tmp/
docker exec -it db psql -U postgres -f /tmp/db_init.sql
docker exec -it db psql -U postgres -d inventorydb -f /tmp/alembic_init.sql
docker exec -it db psql -U app_user -d inventorydb -f /tmp/roles_init.sql
