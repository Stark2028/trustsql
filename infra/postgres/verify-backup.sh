#!/bin/sh
set -eu
# Run only against the local synthetic fixture, using the offline owner.
# A newly created restore database is removed by the trap; the source is untouched.
restore_db="trustsql_restore_check_$$"
restore_created=0
dump_file="$(mktemp /tmp/trustsql-backup-check.XXXXXX)"
cleanup() {
  if [ "$restore_created" = 1 ]; then
    dropdb --username "$POSTGRES_USER" "$restore_db"
  fi
  rm -f -- "$dump_file"
}
trap cleanup EXIT
pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format custom --file "$dump_file"
createdb --username "$POSTGRES_USER" "$restore_db"
restore_created=1
pg_restore --exit-on-error --username "$POSTGRES_USER" --dbname "$restore_db" "$dump_file"
orders="$(psql --username "$POSTGRES_USER" --dbname "$restore_db" --tuples-only --no-align --command 'SELECT COUNT(*) FROM analytics.orders')"
version="$(psql --username "$POSTGRES_USER" --dbname "$restore_db" --tuples-only --no-align --command 'SELECT version FROM control.schema_version WHERE id=1')"
test "$orders" = 60
test "$version" = 1
printf 'Backup/restore check passed: %s synthetic orders, control schema v%s. Source database unchanged.\n' "$orders" "$version"
