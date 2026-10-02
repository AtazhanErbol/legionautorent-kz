#!/bin/sh
set -eu
umask 077
LEGION_ROOT=${LEGION_ROOT:-/srv/legion}
LEGION_ENV_FILE=${LEGION_ENV_FILE:-.env.production}
cd "$LEGION_ROOT"
mkdir -p backups
LEGION_STAMP=$(date -u +%Y%m%dT%H%M%SZ)
docker compose --env-file "$LEGION_ENV_FILE" -f docker-compose.yml exec -T db sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U postgres -d legion --format=custom --no-owner --no-acl' > "backups/legion-$LEGION_STAMP.dump"
docker compose --env-file "$LEGION_ENV_FILE" -f docker-compose.yml exec -T web tar -czf - -C /app media > "backups/media-$LEGION_STAMP.tar.gz"
sha256sum "backups/legion-$LEGION_STAMP.dump" "backups/media-$LEGION_STAMP.tar.gz" > "backups/checksums-$LEGION_STAMP.txt"
printf 'Backup complete: %s\n' "$LEGION_STAMP"
# No automatic retention or deletion. Copy these files to separate protected storage.
