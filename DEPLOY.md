# Развёртывание Legion Auto Rent

Актуальная инструкция для полной переработки от 03.10.2026. Действующий сайт автоматически не переключается. Docker здесь отсутствует: Compose проверен по официальной JSON Schema, Nginx 1.30.5 проверен нативно (конфигурация и HTTP), но Linux image build, контейнерный запуск и выдача сертификата ещё не выполнены.

## 1. Подготовка сервера

Нужны Linux, Git, Docker Engine с Compose v2.20+, Python 3 для генерации секретов, домен и открытые 80/443. Сеть `172.30.0.0/24` не должна пересекаться с существующей инфраструктурой. Если она занята, поменяйте адреса всех трёх сервисов и доверенный адрес Nginx согласованно.

```sh
git clone <URL-ЭТОГО-РЕПОЗИТОРИЯ> /srv/legion
cd /srv/legion
cp .env.production.example .env.production
chmod 600 .env.production
python3 - <<'PY'
import secrets
from pathlib import Path
p = Path('.env.production')
s = p.read_text()
s = s.replace('replace-with-generated-secret-at-least-50-characters-long', secrets.token_urlsafe(64))
s = s.replace('replace-with-generated-admin-password', secrets.token_urlsafe(36))
s = s.replace('replace-with-generated-application-password', secrets.token_urlsafe(36))
p.write_text(s)
PY
docker compose --env-file .env.production -f docker-compose.yml config --quiet
docker compose --env-file .env.production -f docker-compose.yml build
```

Секреты не выводите в журналы. В `.env.production` первоначально `ENVIRONMENT=staging`, `ANALYTICS_ENABLED=false`, `NGINX_CONFIG=./deploy/nginx-bootstrap.conf`. Админка задаётся `ADMIN_PATH` (по умолчанию `control-legion/`); поменяйте при необходимости. Приложение работает от Linux UID 10001 и PostgreSQL-роли `legion` без superuser/CREATEDB. Администратор БД использует отдельный пароль. PostgreSQL 18 монтирует том в `/var/lib/postgresql`, согласно официальному образу.

## 2. Данные: рекомендовано восстановить проверенную копию

Перенесите свежие `.dump`, `media-*.tar.gz` и их контрольные суммы из локального `backups/` на сервер защищённым способом. Дамп может содержать заявки и учётные записи: не помещайте его в публичный каталог. Следующие команды предназначены **только для новой пустой БД**, до первого запуска web.

```sh
docker compose --env-file .env.production -f docker-compose.yml up -d db
# Дождитесь healthy. Подставьте точные имена перенесённых файлов.
docker compose --env-file .env.production -f docker-compose.yml exec -T db sh -c 'PGPASSWORD="$APP_DB_PASSWORD" pg_restore -U legion -d legion --no-owner --no-acl --exit-on-error' < backups/legion-TIMESTAMP.dump
docker compose --env-file .env.production -f docker-compose.yml run --rm --no-deps --entrypoint sh web -c 'tar -xzf /app/backups/media-TIMESTAMP.tar.gz -C /app'
docker compose --env-file .env.production -f docker-compose.yml up -d
```

Проверяйте SHA256 до восстановления. Том media должен быть доступен UID 10001; новый том наследует владельца каталога из image. Не восстанавливайте поверх рабочей БД и не используйте `down -v`. Для существующей установки создайте отдельную БД/том и проверьте восстановление там.

Если копии нет, можно сразу запустить `docker compose --env-file .env.production -f docker-compose.yml up -d --build`. `BOOTSTRAP_LEGACY=true` заполнит только пустой каталог из сохранённых снимков, скачает originals, проверит видео по SHA256, создаст AVIF/WebP и черновики. Первый запуск требует доступа к старому серверу и может занять несколько минут; healthcheck допускает до 20 минут начальной подготовки. Незавершённый первоначальный импорт отмечается в media и возобновляется при повторном запуске. Для уже существующего каталога автоматический импорт пропускается.

```sh
docker compose --env-file .env.production -f docker-compose.yml logs --tail=100 web
docker compose --env-file .env.production -f docker-compose.yml ps
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py migrate --noinput
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py collectstatic --noinput
docker compose --env-file .env.production -f docker-compose.yml exec web python tools/precompress_assets.py --root staticfiles/build
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py createsuperuser
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py restore_legacy_assets
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py verify_migration
```

Entrypoint уже выполняет migrate, createcachetable, collectstatic и precompress. Повторные команды выше нужны для явной проверки. После ручного collectstatic обязательно повторяйте precompress: он обеспечивает лимит gzip для 3D. `import_legacy --dry-run` показывает расхождения; явный `import_legacy` возвращает SEO и цены к live/raw источнику, поэтому после запуска сайта не используйте его как фоновую синхронизацию CMS.

## 3. HTTPS и включение production

DNS должен указывать на сервер для обоих имён. Bootstrap Nginx обслуживает ACME challenge по HTTP; приложение пока закрыто от индексации и требует HTTPS. Это стадия выдачи сертификата.

```sh
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm certbot certonly --webroot -w /var/www/acme -d legionautorent.kz -d www.legionautorent.kz --email YOUR-EMAIL --agree-tos --no-eff-email
```

После выдачи сертификата установите в `.env.production` `NGINX_CONFIG=./deploy/nginx.conf`, затем:

```sh
docker compose --env-file .env.production -f docker-compose.yml up -d --force-recreate nginx
docker compose --env-file .env.production -f docker-compose.yml exec nginx nginx -t
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py check --deploy
```

До открытия проверьте формы, медиа, языки, 27 проблемных URL и legal/переводные черновики. Затем установите `ENVIRONMENT=production`, `ANALYTICS_ENABLED=true`, пересоздайте web и nginx. Убедитесь, что robots разрешает обход и у публичных RU-страниц больше нет `X-Robots-Tag: noindex`. HTTP и www переходят одним 301 на HTTPS без www с сохранением пути/параметров. HSTS включается только в production.

GTM, GA4 и Метрика сохранены. Если задан GTM, клиент загружает его первым и не вставляет отдельные дубли GA4/Метрики. Проверьте содержимое GTM-KJWPLLN в Tag Assistant: нет доступа к настройкам контейнера, поэтому наличие нужных тегов внутри нельзя подтвердить локально. Карта загружается после открытия пользователем; телефон/WhatsApp работают без JS.

## 4. Копии, cron, обновление и откат

```sh
LEGION_ROOT=/srv/legion sh deploy/backup-compose.sh
# Пример crontab (пользователь с доступом к Docker):
# 15 2 * * * LEGION_ROOT=/srv/legion /bin/sh /srv/legion/deploy/backup-compose.sh >> /srv/legion/backups/cron.log 2>&1
# 20 3 * * * cd /srv/legion && docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm certbot renew --webroot -w /var/www/acme --quiet && docker compose --env-file .env.production -f docker-compose.yml exec -T nginx nginx -s reload
```

Скрипт делает custom pg_dump, архив всего media и SHA256; ничего автоматически не удаляет. Храните отдельную зашифрованную копию вне сервера. Для приложения с частыми загрузками делайте резервирование в окне без изменений media. Проверяйте восстановление в изолированной БД регулярно.

Перед обновлением: backup, зафиксировать текущий commit/image ID, получить новый код, собрать image, выполнить проверки на staging и затем `up -d --build`. Не удаляйте прежние images/тома. Для отката кода используйте сохранённый image/commit с совместимой схемой; добавляющие миграции этой версии не требуют удаления колонок. Если откатывается БД, восстановите копию в **новую** БД и согласованное media, проверьте их и только затем переключите конфигурацию. Откат к `d5e7e0a` вернёт старый отклонённый интерфейс; это аварийный checkpoint, не новая production-версия.

## 5. Docker для разработки

```sh
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
# http://127.0.0.1:8080/ ; /control-legion/
```

Dev-Compose использует отдельные тома, только loopback-порт и заведомо локальные пароли. Эти значения не подходят production. Не запускайте одновременно обе конфигурации как единый merged stack. Старый `compose.yaml` — только include production-конфигурации, для однозначности выше всегда указано `-f`.

Источники конфигурации: [PostgreSQL Docker](https://hub.docker.com/_/postgres), [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/), [Nginx](https://nginx.org/en/download.html). Отчёт о фактически выполненных проверках — `reports/deployment_validation.json` и `reports/nginx_http.json`.
