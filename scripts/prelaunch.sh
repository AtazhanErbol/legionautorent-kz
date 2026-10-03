#!/bin/sh
set -eu
# Run in the existing environment, or inside web through docker compose exec.
# Does not import data, run migrations, submit leads or change the deployment.
BASE_URL=${1:-${SITE_URL:-https://legionautorent.kz}}
PYTHON=${PYTHON:-python}
"$PYTHON" manage.py check --deploy
"$PYTHON" manage.py verify_migration
"$PYTHON" manage.py release_check --base-url "$BASE_URL"
