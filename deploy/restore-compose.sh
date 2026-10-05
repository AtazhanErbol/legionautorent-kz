#!/bin/sh
# Restore only into a NEW, empty installation; never overwrite live data.
set -eu
umask 077
LEGION_ROOT=${LEGION_ROOT:-/srv/legion}
LEGION_ENV_FILE=${LEGION_ENV_FILE:-.env.production}
cd "$LEGION_ROOT"
LEGION_DUMP=${1:?Usage: restore-compose.sh backups/legion-TIMESTAMP.dump backups/media-TIMESTAMP.tar.gz}
LEGION_MEDIA=${2:?Supply the corresponding media archive}
# Verify the matching manifest, bytes and archive BEFORE starting any container.
if [ "$#" -ge 3 ]; then
    python3 deploy/verify_backup.py "$LEGION_DUMP" "$LEGION_MEDIA" --manifest "$3"
else
    python3 deploy/verify_backup.py "$LEGION_DUMP" "$LEGION_MEDIA"
fi
compose() { docker compose --env-file "$LEGION_ENV_FILE" -f docker-compose.yml "$@"; }
compose up -d --wait db
LEGION_TABLES=$(compose exec -T db sh -c 'PGPASSWORD="$APP_DB_PASSWORD" psql -U legion -d legion -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\''"')
test "$LEGION_TABLES" = 0 || { printf '%s\n' 'Refusing restore: database is not empty.' >&2; exit 1; }
compose run --rm --no-deps --entrypoint sh web -c 'test -z "$(find /app/media -mindepth 1 -print -quit)"' || { printf '%s\n' 'Refusing restore: media volume is not empty.' >&2; exit 1; }
compose exec -T db sh -c 'PGPASSWORD="$APP_DB_PASSWORD" pg_restore -U legion -d legion --no-owner --no-acl --exit-on-error' < "$LEGION_DUMP"
compose run --rm -T --no-deps --entrypoint sh web -c 'tar -xzf - -C /app --no-same-owner' < "$LEGION_MEDIA"
compose up -d --wait web
compose exec -T web python manage.py configure_hero_video
printf '%s\n' 'Restored. Verify the catalogue and media before starting public Nginx.'
