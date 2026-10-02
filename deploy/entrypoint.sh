#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py createcachetable
if [ "${BOOTSTRAP_LEGACY:-false}" = true ]; then
    python manage.py bootstrap_legacy
fi
python manage.py collectstatic --noinput
python tools/precompress_assets.py --root staticfiles/build
exec "$@"
