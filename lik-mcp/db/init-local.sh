#!/bin/bash
# Create the persistent local-testing database `likdb_local` and load the schema.
#
# Runs from the Postgres image entrypoint, after 01-init.sql (lexical order). The
# entrypoint default DB (likdb_test) is for the pytest suite, which TRUNCATEs; manual
# testing needs data that survives, so it uses a separate likdb_local.
#
# CAVEAT: docker-entrypoint-initdb.d scripts run ONLY when the data volume is first
# initialized (empty). On an existing volume this never runs — create the DB by hand:
#   docker compose exec db createdb -U lik likdb_local
#   LIK_DB_NAME=likdb_local uv run python scripts/init_db.py
set -e

# Idempotent create: only if the database is absent (guards re-init edge cases).
# Connect to the default DB ("$POSTGRES_DB"); psql with no -d would target a DB named
# after the user, which does not exist.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d "$POSTGRES_DB" <<-'EOSQL'
	SELECT 'CREATE DATABASE likdb_local'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'likdb_local')\gexec
EOSQL

# Apply the same idempotent schema 01-init.sql loaded into the default DB.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d likdb_local \
	-f /docker-entrypoint-initdb.d/01-init.sql
