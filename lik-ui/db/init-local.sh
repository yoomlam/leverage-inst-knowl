#!/bin/bash
# Create the persistent local-testing database `likuidb_local` and load the schema.
#
# Runs from the Postgres image entrypoint, after 01-init.sql (lexical order). The
# entrypoint default DB (likuidb_test) is for the pytest suite, which TRUNCATEs; manual
# testing needs data that survives, so it uses a separate likuidb_local.
#
# CAVEAT: docker-entrypoint-initdb.d scripts run ONLY when the data volume is first
# initialized (empty). On an existing volume this never runs — create the DB by hand:
#   docker compose exec db createdb -U lik likuidb_local
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d "$POSTGRES_DB" <<-'EOSQL'
	SELECT 'CREATE DATABASE likuidb_local'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'likuidb_local')\gexec
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d likuidb_local \
	-f /docker-entrypoint-initdb.d/01-init.sql
