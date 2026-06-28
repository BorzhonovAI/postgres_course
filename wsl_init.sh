#!/usr/bin/env bash
# Starts PostgreSQL Docker container and initializes the database.
# Safe to re-run — init SQL files are idempotent.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# Start container (idempotent — starts only if not running)
docker compose up -d

# Copy init SQL into container
docker cp "$SCRIPT_DIR/db_init.sql" db:/tmp/
docker cp "$SCRIPT_DIR/roles_init.sql" db:/tmp/
docker cp "$SCRIPT_DIR/alembic_init.sql" db:/tmp/
docker cp "$SCRIPT_DIR/auth_init.sql" db:/tmp/

# Execute in order
docker exec -it db psql -U postgres -f /tmp/db_init.sql
docker exec -it db psql -U postgres -d inventorydb -f /tmp/alembic_init.sql
docker exec -it db psql -U app_user -d inventorydb -f /tmp/roles_init.sql
docker exec -it db psql -U app_user -d inventorydb -f /tmp/auth_init.sql
