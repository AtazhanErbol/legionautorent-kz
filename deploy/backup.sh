#!/bin/sh
set -eu
umask 077
: "${DATABASE_URL:?DATABASE_URL is required}"
LEGION_ROOT=${LEGION_ROOT:-/srv/legion}
LEGION_BACKUP_DIR=${LEGION_BACKUP_DIR:-/srv/legion/backups}
mkdir -p "$LEGION_BACKUP_DIR"
LEGION_TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
# libpq reads the connection URL from the environment rather than process arguments.
export PGDATABASE="$DATABASE_URL"
pg_dump --format=custom --no-owner --no-acl --file="$LEGION_BACKUP_DIR/legion-$LEGION_TIMESTAMP.dump"
tar -czf "$LEGION_BACKUP_DIR/media-$LEGION_TIMESTAMP.tar.gz" -C "$LEGION_ROOT" media
sha256sum "$LEGION_BACKUP_DIR/legion-$LEGION_TIMESTAMP.dump" "$LEGION_BACKUP_DIR/media-$LEGION_TIMESTAMP.tar.gz" > "$LEGION_BACKUP_DIR/checksums-$LEGION_TIMESTAMP.txt"
printf 'Backup created: %s\n' "$LEGION_TIMESTAMP"
# Retention/deletion is deliberately left to the owner policy; copy backups off-host.
