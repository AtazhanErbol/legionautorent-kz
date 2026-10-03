PYTHON ?= python
COMPOSE ?= docker compose --env-file .env.production
BASE_URL ?= https://legionautorent.kz

.PHONY: up down test seo-test release-check backup
up:
	$(COMPOSE) up -d --build
down:
	$(COMPOSE) down
test:
	$(PYTHON) manage.py test --settings=legion.config.testing --keepdb --noinput
seo-test:
	$(PYTHON) manage.py test seo.test_release --settings=legion.config.testing --keepdb --noinput
	$(PYTHON) manage.py verify_migration
release-check:
	$(PYTHON) manage.py release_check --base-url $(BASE_URL)
backup:
	LEGION_ROOT="$(CURDIR)" sh deploy/backup-compose.sh
