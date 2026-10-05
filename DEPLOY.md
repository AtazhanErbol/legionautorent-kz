# Развёртывание Legion Auto Rent

Актуальная инструкция от 05.10.2026. Действующий сайт автоматически не переключается. Docker здесь отсутствует: Compose проверен по официальной JSON Schema, Nginx 1.30.5 проверен нативно (конфигурация и HTTP), но Linux image build, контейнерный запуск и выдача сертификата ещё не выполнены.

Первый экран использует готовое видео владельца `design_refs/hero/hero-source.mp4`. Публикуется только подготовленная версия: **1280×720, 60 fps, 7,5 с, 3 673 288 байт**, CRF 20, GOP 8, без звука, faststart. Промежуточные кадры рассчитаны из исходных 24 fps по просьбе владельца улучшить плавность. Последние 2,5 с исключены из-за искажённых задних надписей. Генерация и апскейл не нужны. MP4 и три WebP с хешем имени находятся в `static/hero/`. `core/hero.py` обслуживает выбранный в CMS файл; исходный MP4 не требуется для запуска готовой сборки. Четыре подписи сопровождают сцену 500svh; H1 остаётся точным SEO-полем города. Первым появляется постер кадра 0; мобильный режим использует кадр 3,5 с с ручной кнопкой просмотра. Конечный кадр используется в партнёрском блоке. Подробности: `reports/SHOWROOM_HERO_REPORT.md`. Старые ролики, GLB и исходники сохранены; исходники исключены из Docker и активной сборки.

Перед запуском примените новые миграции `core.0006` и `seo.0004` обычным `manage.py migrate`, затем `manage.py configure_hero_video`. Команда выбирает текущий комплект медиа; её не нужно запускать после намеренной смены файлов владельцем в CMS. Свежая проверенная резервная копия до изменений — `20261005T083825Z`.

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

Свежая проверенная копия: `legion-20261005T055453Z.dump`, `media-20261005T055453Z.tar.gz` и `manifest-20261005T055453Z.json`. Восстановление в отдельной локальной БД подтвердило 91 автомобиль, 4 города и 302 связи изображений; архив содержит 3893 медиафайла. Более ранние резервные копии сохранены.

```sh
# Проверка файлов без подключения к БД или Docker; подставьте точный TIMESTAMP.
python3 deploy/verify_backup.py backups/legion-TIMESTAMP.dump backups/media-TIMESTAMP.tar.gz
# Восстановление только в новую пустую установку; повторяет проверку автоматически.
LEGION_ROOT=/srv/legion sh deploy/restore-compose.sh backups/legion-TIMESTAMP.dump backups/media-TIMESTAMP.tar.gz
```

Проверка сверяет SHA256 с `manifest-TIMESTAMP.json` из локального backup или `checksums-TIMESTAMP.txt` из `backup-compose.sh`. Этот файл должен лежать рядом с дампом; его можно передать третьим аргументом скрипта восстановления (либо через `--manifest` проверяющей программе). Без него, при повреждении файлов, несовпадении дат, небезопасных путях или ссылках внутри архива скрипт останавливается **до обращения к Docker**. Контрольные суммы обнаруживают повреждение; получайте и архив, и manifest из доверенного источника.

Том media должен быть доступен UID 10001; новый том наследует владельца каталога из image. Не восстанавливайте поверх рабочей БД и не используйте `down -v`. Для существующей установки создайте отдельную БД/том и проверьте восстановление там.

Автоматического импорта при запуске нет. Entrypoint выполняет только миграции, подготовку кеша и статических файлов. При отсутствии копии сначала вручную восстановите достоверные данные; не включайте пустой каталог в production. Скрипт восстановления дополнительно отказывается работать с непустой БД или media. После частично неудачного восстановления сохраните эту установку для диагностики и повторите в новой БД/томах.

```sh
docker compose --env-file .env.production -f docker-compose.yml logs --tail=100 web
docker compose --env-file .env.production -f docker-compose.yml ps
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py migrate --noinput
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py configure_hero_video
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py collectstatic --noinput
docker compose --env-file .env.production -f docker-compose.yml exec web python tools/precompress_assets.py --root staticfiles/build
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py createsuperuser
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py restore_legacy_assets
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py verify_migration
```

Entrypoint уже выполняет migrate, createcachetable, collectstatic и precompress. Повторные команды выше нужны для явной проверки. `configure_hero_video` — отдельный явный шаг: он проверяет готовые файлы, включает видео, отключает 3D, задаёт пути и очищает кеш; каталог, SEO и заявки не импортируются. Повтор команды безопасен для этих данных. После ручного collectstatic повторяйте precompress для актуальных сжатых JS/CSS-ресурсов. `import_legacy --dry-run` показывает расхождения; явный `import_legacy` возвращает SEO и цены к live/raw источнику, поэтому после запуска сайта не используйте его как фоновую синхронизацию CMS.

Проверьте в Site Settings видео, постер, мобильный постер, финальный кадр, флаг анимации и переводы финальной подписи. H1 по-прежнему берётся из SEO города. Элементы управления 3D убраны из админки; старые поля БД сохранены для обратимости. `configure_hero_video` явно переключает на утверждённые локальные ассеты, не импортируя каталог.


### Пользователи контейнеров и сертификаты

Web работает с UID 10001, PostgreSQL — от `postgres`, Nginx — с UID/GID 101. Nginx слушает непривилегированные 8080/8443 внутри контейнера, снаружи опубликованы обычные 80/443; временные файлы и PID пишутся в `/tmp`. Для новой установки используются новые именованные тома с правами исходного image. При переносе существующих томов проверьте владельцев до запуска. Этот Docker-проход локально проверить невозможно: Docker отсутствует.

После первого получения и каждого обновления сертификата предоставьте его чтение группе Nginx, затем перезапустите Nginx:

```sh
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm --entrypoint sh certbot /opt/certificate-permissions.sh
docker compose --env-file .env.production -f docker-compose.yml up -d --force-recreate nginx
```

Ключ не становится общедоступным. Certbot — отдельный одноразовый служебный профиль; постоянно работающие сервисы запускаются без root. Общий кеш и лимиты запросов используют PostgreSQL; Redis не обязателен.

## 3. HTTPS и включение production

DNS должен указывать на сервер для обоих имён. Bootstrap Nginx обслуживает ACME challenge по HTTP; приложение пока закрыто от индексации и требует HTTPS. Это стадия выдачи сертификата.

```sh
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm certbot certonly --webroot -w /var/www/acme -d legionautorent.kz -d www.legionautorent.kz --email YOUR-EMAIL --agree-tos --no-eff-email
```

После выдачи сертификата предоставьте группе Nginx доступ к ключу (команда ниже), установите в `.env.production` `NGINX_CONFIG=./deploy/nginx.conf`, затем:

```sh
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm --entrypoint sh certbot /opt/certificate-permissions.sh
docker compose --env-file .env.production -f docker-compose.yml up -d --force-recreate nginx
docker compose --env-file .env.production -f docker-compose.yml exec nginx nginx -t
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py check --deploy
```

До открытия проверьте формы, медиа, языки, 27 проблемных URL и legal/переводные черновики. Для этих 27 URL сохраняется 404 без массовых перенаправлений и без включения в sitemap; восстановление карточек требует отдельных достоверных данных. Ролик сгенерирован Hailuo по кадрам владельца и утверждён им. Затем установите `ENVIRONMENT=production`, `ANALYTICS_ENABLED=true`, пересоздайте web и nginx. Убедитесь, что robots разрешает обход и у публичных RU-страниц больше нет `X-Robots-Tag: noindex`. HTTP и www переходят одним 301 на HTTPS без www с сохранением пути/параметров. HSTS включается только в production.

Идентификаторы GTM, GA4 и Метрики сохранены, но приложение подключает **только GTM**. Владелец проверяет внутри `GTM-KJWPLLN` наличие Яндекс Метрики **92545653** и GA4 **G-00P3VJTEK9**, затем проверяет события в Tag Assistant. Отдельного подключения GA4/Метрики и запасной прямой загрузки при пустом GTM нет. Доступа к настройкам контейнера локальная проверка не предоставляет. Карта загружается после открытия пользователем; телефон/WhatsApp работают без JS.

После HTTPS проверьте видео и диапазонную загрузку:

```sh
curl -I https://legionautorent.kz/static/hero/mercedes-segment-01-43d4cc20ca42.mp4
curl -sS -D - -o /dev/null -H 'Range: bytes=0-1023' https://legionautorent.kz/static/hero/mercedes-segment-01-43d4cc20ca42.mp4
curl -I https://legionautorent.kz/static/hero/mercedes-front-77ca8545d4d0.webp
curl -I https://legionautorent.kz/static/hero/mercedes-front-mobile-940302853d4f.webp
```

Ожидаются MP4 с `Content-Type: video/mp4`, ответ 206 с корректным `Content-Range` на запрос диапазона и 200 для постеров. В браузере проверить прямую, обратную и быструю прокрутку через всю сцену, кнопку перехода к каталогу и отсутствие пустого промежутка после закрепления. На ширине менее 900 px, при уменьшении движения и экономии трафика должна оставаться полный статический первый экран с поиском без запроса MP4. Намеренно заблокированный файл видео также не должен удерживать страницу. Видео не запускается само после остановки прокрутки. Проверить изменение размера окна и возврат назад в истории. Обновлённые лабораторные показатели смотреть в `PERFORMANCE_REPORT.md`; production-аналитика, сеть сервера и полевой INP требуют отдельной проверки после публикации.

## 4. Копии, cron, обновление и откат

```sh
LEGION_ROOT=/srv/legion sh deploy/backup-compose.sh
# Пример crontab (пользователь с доступом к Docker):
# 15 2 * * * LEGION_ROOT=/srv/legion /bin/sh /srv/legion/deploy/backup-compose.sh >> /srv/legion/backups/cron.log 2>&1
# 20 3 * * * cd /srv/legion && docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm certbot renew --webroot -w /var/www/acme --quiet --deploy-hook "sh /opt/certificate-permissions.sh" && docker compose --env-file .env.production -f docker-compose.yml exec -T nginx nginx -s reload
```

Скрипт делает custom pg_dump, архив всего media и SHA256; ничего автоматически не удаляет. Храните отдельную зашифрованную копию вне сервера. Для приложения с частыми загрузками делайте резервирование в окне без изменений media. Проверяйте восстановление в изолированной БД регулярно.

Перед обновлением: backup, зафиксировать текущий commit/image ID, получить новый код, собрать image, выполнить проверки на staging и затем `up -d --build`. Не удаляйте прежние images/тома. Для отката кода используйте сохранённый image/commit с совместимой схемой; добавляющие миграции этой версии не требуют удаления колонок. Если откатывается БД, восстановите копию в **новую** БД и согласованное media, проверьте их и только затем переключите конфигурацию. Откат к `d5e7e0a` вернёт старый отклонённый интерфейс; это аварийный checkpoint, не новая production-версия.

Точка перед завершением — тег `codex/checkpoint-before-final-hero-20261004` и manifest `20261003T223851Z`. Для аварийной статической версии отключите «Анимация при прокрутке» в Site Settings: постер, H1, поиск и каталог сохранятся. Текущие миграции добавляют поля, не удаляя данные.

## 5. Docker для разработки

```sh
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
# http://127.0.0.1:8080/ ; /control-legion/
```

Dev-Compose использует отдельные тома, только loopback-порт и заведомо локальные пароли. Эти значения не подходят production. Не запускайте одновременно обе конфигурации как единый merged stack. Старый `compose.yaml` — только include production-конфигурации, для однозначности выше всегда указано `-f`.

Источники конфигурации: [PostgreSQL Docker](https://hub.docker.com/_/postgres), [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/), [Nginx](https://nginx.org/en/download.html). Отчёт о фактически выполненных проверках — `reports/deployment_validation.json` и `reports/nginx_http.json`.
