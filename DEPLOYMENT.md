> Исторический документ предыдущей реализации. Актуальные решения от 03.10.2026: README.md, DEPLOY.md и reports/SEO_MIGRATION_REPORT.md.

# Deployment: Legion Auto Rent

## Проверено локально

Django 5.2.17, PostgreSQL 18.6, отдельный кластер `.local/postgres`, bind 127.0.0.1:55432. Новый сайт доступен на 127.0.0.1:8000. Production domain не переключался. Linux Gunicorn/Nginx и Docker-конфигурация подготовлены, но в этом Windows-окружении не запускались.

Проект содержит миграции, lock зависимостей, самодостаточные static assets, Django PO/MO, HTTP snapshot, импорт и отчёты. `media/`, `.env`, `.local/`, backup archives и node_modules исключены из Git и Docker build. **Они существуют локально и должны переноситься отдельно.** Секреты и admin-access файл в репозиторий не включать.

## Staging на Linux

1. Создать отдельного системного пользователя `legion`, каталог `/srv/legion`, отдельную PostgreSQL DB/роль без superuser. DB и Gunicorn доступны только localhost/private network. Старую DB и текущий production не изменять.
2. Python 3.12+, PostgreSQL client (pg_dump/pg_restore той же или более новой major version), Nginx, systemd. Установить requirements.lock в `.venv`; npm для запуска не нужен — vendor assets сохранены.
3. Скопировать `.env.example` в `.env`, сгенерировать уникальный SECRET_KEY; задать `ENVIRONMENT=staging`, `DEBUG=false`, PostgreSQL DATABASE_URL, `ALLOWED_HOSTS=new.legionautorent.kz`, `SITE_URL=https://new.legionautorent.kz`, `CSRF_TRUSTED_ORIGINS=https://new.legionautorent.kz`, `SECURE_SSL_REDIRECT=true`, `ANALYTICS_ENABLED=false`. `.env` доступен только пользователю сервиса (chmod 600). Если DB удалённая — TLS с проверкой сертификата/hostname.
4. Выполнить последовательно:

```sh
python manage.py migrate
python manage.py createcachetable
python manage.py migrate_legion_data --dry-run
python manage.py migrate_legion_data
python manage.py seed_content
python manage.py setup_roles
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py check --deploy
```

5. Для media скопировать **всю** папку `media/` и manifest. При скачивании заново `python manage.py migrate_legion_data --download-images`; после media-copy повторить обычный импорт. Для сохранения правок CMS не использовать --refresh без проверки snapshot и DB backup.
6. Установить deploy/legion.service и адаптировать пути/пользователя. Nginx staging config — deploy/staging-nginx.conf. Создать отдельный htpasswd для staging. Gunicorn bind только 127.0.0.1:8001. Nginx всегда перезаписывает X-Real-IP и X-Forwarded-*; приложение доверяет лишь известным proxy (TRUST_PROXY_HEADERS=true). Для native systemd задать TRUSTED_PROXY_IPS=127.0.0.1,::1. В Docker Compose явно задать реальный peer IP Nginx или Docker gateway: localhost хоста внутри контейнера имеет другой адрес. Проверить REMOTE_ADDR и ограничения попыток через Nginx; не использовать wildcard и не доверять произвольным клиентским заголовкам. Если добавляется CDN/proxy — отдельно настроить его реальные IP.
7. Получить сертификат для staging через ACME/Certbot. Для HTTP challenge сначала настроить простой HTTP server с /.well-known/acme-challenge/; только после получения сертификата включить HTTPS конфигурацию. Проверить автоматическое продление и `nginx -t`.
8. У пользователя legion должны быть права записи в media и backups, чтения staticfiles. Загруженные файлы Nginx обслуживает только как static; PHP/CGI handlers для `/media/` не подключать.

## Docker (альтернативный способ)

Dockerfile/compose.yaml запускают app и PostgreSQL 18, Gunicorn порт доступен с хоста только на loopback. Нужны `POSTGRES_PASSWORD` (случайный hex для безопасного URI), production/staging `.env`, записываемые app uid 10001 bind directories media/staticfiles/backups. `PGDATA` задан явно; менять major version существующего DB volume без pg_upgrade/dump-restore нельзя.

```sh
docker compose up -d db
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createcachetable
docker compose run --rm web python manage.py migrate_legion_data
docker compose run --rm web python manage.py seed_content
docker compose run --rm web python manage.py setup_roles
docker compose run --rm web python manage.py collectstatic --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose up -d web
```

Nginx/SSL на хосте всё равно обязательны. Docker pipeline здесь не проверен: локальная проверка выполнена непосредственно на PostgreSQL 18.

## Backup и восстановление

Локально создан backup DB/media и проверено восстановление в отдельную временную DB; backup_report.json содержит имена, SHA-256 и counts. Это backup новой локальной версии, не приватной старой production DB.

В production перед изменениями снять старую DB, старые uploads и конфигурацию. Для новой версии использовать deploy/backup.sh через защищённый environment file пользователя legion. Назначить ежедневный systemd timer или существующий backup scheduler; хранить зашифрованную копию вне сервера, контролировать успех и срок хранения. Архивы содержат персональные данные заявок: права доступа 600, доступ только ответственных операторов. Секреты резервировать отдельно в защищённом хранилище.

Проверка восстановления: создать **новую пустую проверочную** DB, `pg_restore --exit-on-error --no-owner --no-acl -d <test_db> <dump>`, проверить counts, сайт и формы. Media извлекать в отдельный проверочный каталог, проверить checksum и изображения. Не восстанавливать поверх работающей DB. Выполнить полную репетицию rollback до смены домена.

## Gate перед production

- Закрыть 27 недоступных legacy карточек: данные из старой БД либо подтверждённые индивидуальные 301. Не redirect всех на главную.
- Проверить классификацию 91 автомобиля. Дополнить характеристики и точные условия: возраст/стаж/депозит/оплата/пробег. Уточнить адрес Павлодара.
- Владелец должен утвердить юридические drafts /privacy/ и /consent/ в Admin (legal_approved). Это исходные рабочие тексты, не юридически утверждённые документы.
- Заполнить/проверить KZ/EN контент и партнёрские сообщения в Admin. Публиковать флажком только полный перевод. Незаполненные версии остаются noindex, absent from sitemap/hreflang.
- GLB hero включать только с подтверждённой лицензией до 5 MB. В текущем состоянии — оптимизированное фото. Three.js/Draco локальные, init по запросу на desktop; mobile, reduced motion, save-data используют фото.
- Проверить существующий GTM-KJWPLLN: не дублировать GA4 G-00P3VJTEK9 и Метрику 92545653 через контейнер и прямые snippets. Проверить события click_phone, click_whatsapp, booking_start/submit, view_car/city, filter_cars, select_city без передачи PII. На local/staging analytics выключена.
- Повторить `python manage.py test`, crawl, browser smoke и lab performance на staging. Проверить production URL с HTTPS, реальные формы/CSRF, logs, redirects, sitemap, schema Rich Results Test.

## Переключение и rollback

Переключать только после backup/restore и закрытия gate. В `.env` задать `ENVIRONMENT=production`, `DEBUG=false`, production SITE_URL/hosts/origins, `ANALYTICS_ENABLED=true`; использовать deploy/nginx.conf, убрать staging Basic Auth и staging X-Robots-Tag из Nginx. Django автоматически исключит глобальный staging noindex. Проверить robots: разрешено публичное содержимое, не весь `/` закрыт. Для hostname www и HTTP — один 301 на основную HTTPS версию.

Сохранить старый release/server и media. Rollback — вернуть routing к сохранённой версии; заявки, пришедшие в новую DB, экспортировать перед откатом и согласовать перенос. Не удалять новую DB и 301 правила.

После запуска отправить sitemap в Google Search Console и Яндекс.Вебмастер с существующими verification IDs, проверить coverage/404/органический трафик и полевые CWV. Эти действия требуют доступа владельца; они не выполнены локальной разработкой.

Официальные проверки: [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).
