#!/bin/bash

cd /home/anatoly/work/projects/postgres_course
docker compose up -d
docker cp /home/anatoly/work/projects/postgres_course/db_init.sql db:/tmp/
docker cp /home/anatoly/work/projects/postgres_course/alembic_init.sql db:/tmp/
docker exec -it db psql -U postgres -f /tmp/db_init.sql
docker exec -it db psql -U postgres -d inventorydb -f /tmp/alembic_init.sql
cd /home/anatoly/work/projects/postgres_course/pg-course-template &&
python3 -m venv .venv &&
source .venv/bin/activate &&
pip install -r requirements.txt &&
alembic downgrade base &&
alembic upgrade head
