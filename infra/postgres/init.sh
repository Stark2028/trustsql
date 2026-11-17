#!/bin/sh
set -eu
# Secrets are read inside psql; never interpolate them into shell SQL or command arguments.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 <<'SQL'
\getenv reader_password TRUSTSQL_READER_PASSWORD
\getenv control_password TRUSTSQL_CONTROL_PASSWORD
CREATE ROLE trustsql_reader LOGIN PASSWORD :'reader_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE trustsql_control LOGIN PASSWORD :'control_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CONNECT, TEMPORARY ON DATABASE trustsql FROM PUBLIC;
GRANT CONNECT ON DATABASE trustsql TO trustsql_reader, trustsql_control;
CREATE SCHEMA analytics AUTHORIZATION trustsql_owner;
CREATE SCHEMA control AUTHORIZATION trustsql_control;
GRANT USAGE ON SCHEMA analytics TO trustsql_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE trustsql_owner IN SCHEMA analytics GRANT SELECT ON TABLES TO trustsql_reader;
ALTER ROLE trustsql_reader IN DATABASE trustsql SET default_transaction_read_only = on;
ALTER ROLE trustsql_reader IN DATABASE trustsql SET statement_timeout = '5s';
ALTER ROLE trustsql_reader IN DATABASE trustsql SET lock_timeout = '1s';
SQL

