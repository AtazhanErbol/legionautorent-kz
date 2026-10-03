#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py collectstatic --noinput
python tools/precompress_assets.py --root staticfiles/build
exec "$@"
