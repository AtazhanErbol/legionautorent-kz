# Развёртывание LEGIONAUTORENT на PS.kz

Этот проект рассчитан на отдельный VPS / Cloud-сервер с SSH и Docker Compose. Инструкция использует Ubuntu 24.04 LTS, PostgreSQL 18, Django, Gunicorn и Nginx. Обычный тариф общего PHP-хостинга для этой конфигурации не подходит без отдельной поддержки Python и контейнеров.

Исходный локальный проект и работающий PythonAnywhere не переключаются этими подготовительными действиями. GitHub хранит код. База, изображения, заявки, учётные записи и пароли переносятся отдельными закрытыми резервными копиями.

## 1. Доступ к серверу

Создайте или используйте сервер PS.kz с Ubuntu, внешним IP и SSH-ключом. Для небольшого каталога отправная конфигурация — 2 vCPU, 4 ГБ памяти и диск 30 ГБ; окончательный размер зависит от медиа и резервных копий. Откройте входящие 22 для своего IP и 80/443 для сайта. PostgreSQL 5432 и приложение 8001 наружу не публикуются.

Порядок создания и подключения описан в [документации PS.kz](https://docs.ps.kz/ru/cloud/cloud-server/quickstart/create-vm) и [руководстве по SSH](https://docs.ps.kz/ru/cloud/cloud-server/quickstart/vm-remote-connect). Имя пользователя берите из выбранного образа и панели, не предполагайте, что оно всегда `root`.

Установите Docker Engine и Compose Plugin по [официальной инструкции для Ubuntu](https://docs.docker.com/engine/install/ubuntu/). Проверьте на сервере:

```sh
sudo docker version
sudo docker compose version
sudo docker run --rm hello-world
sudo apt install git python3
```

Далее команды Docker выполняются пользователем, которому уже предоставлен доступ к Docker. Если такого доступа нет, используйте `sudo docker`.

## 2. Скачать чистый проект

```sh
sudo install -d -m 0755 /srv/legion
sudo chown "$(id -u):$(id -g)" /srv/legion
git clone --branch main https://github.com/AtazhanErbol/legionautorent-kz.git /srv/legion
cd /srv/legion
cp .env.production.example .env.production
chmod 600 .env.production
mkdir -p backups
chmod 700 backups
```

Репозиторий закрытый. Используйте свой доступ GitHub или отдельный SSH deploy key только для чтения; не вставляйте токен в URL репозитория или в файлы проекта.

Сгенерируйте три независимых значения: `SECRET_KEY`, `POSTGRES_PASSWORD` и `APP_DB_PASSWORD`. Для каждого отдельно выполните:

```sh
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Откройте `.env.production` редактором. Перенесите значения в соответствующие строки; пароль приложения повторите внутри `DATABASE_URL`. URL-safe генерация позволяет не экранировать пароль в URL. На стадии проверки:

```dotenv
ENV_FILE=.env.production
ENVIRONMENT=staging
DEBUG=false
SITE_URL=https://legionautorent.kz
ALLOWED_HOSTS=legionautorent.kz,www.legionautorent.kz,localhost,127.0.0.1,nginx
CSRF_TRUSTED_ORIGINS=https://legionautorent.kz
SECURE_SSL_REDIRECT=false
ANALYTICS_ENABLED=false
NGINX_CONFIG=./deploy/nginx-bootstrap.conf
```

Не коммитьте этот файл. `staging` закрывает сайт от индексации, сохраняя исходные canonical URL. Не меняйте SITE_URL на адрес сервера или PythonAnywhere.

## 3. Перенести базу и изображения

На локальном компьютере создайте свежую пару копий:

```powershell
Set-Location D:\legionautorent.kz
& .venv\Scripts\python.exe -X utf8 tools\backup_local.py
```

Нужны три файла с одной датой: `legion-TIMESTAMP.dump`, `media-TIMESTAMP.tar.gz`, `manifest-TIMESTAMP.json`. Скопируйте их из `backups` на сервер в `/srv/legion/backups` через SCP/SFTP. Они содержат закрытые данные; в GitHub их не загружайте.

На сервере, заменив TIMESTAMP фактической датой:

```sh
cd /srv/legion
python3 deploy/verify_backup.py backups/legion-TIMESTAMP.dump backups/media-TIMESTAMP.tar.gz --manifest backups/manifest-TIMESTAMP.json
docker compose --env-file .env.production -f docker-compose.yml config --quiet
docker compose --env-file .env.production -f docker-compose.yml build web
LEGION_ROOT=/srv/legion LEGION_ENV_FILE=.env.production sh deploy/restore-compose.sh backups/legion-TIMESTAMP.dump backups/media-TIMESTAMP.tar.gz backups/manifest-TIMESTAMP.json
docker compose --env-file .env.production -f docker-compose.yml up -d --wait nginx
```

Восстановление допускается только в новую пустую БД и пустой том media. Скрипт проверяет контрольные суммы, формат и безопасность архива, затем отказывается перезаписывать непустую установку. Не используйте `docker compose down -v`: это удаляет данные.

Docker собирает frontend сам. FFmpeg на сервере не нужен: новый мастер, оба набора кадров и постеры уже включены в репозиторий. При старте выполняются migrate, подготовка кеша, collectstatic и сжатие JS/CSS; импорт каталога автоматически не запускается.

## 4. Проверить до переключения домена

```sh
docker compose --env-file .env.production -f docker-compose.yml ps
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py check
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py verify_migration
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py release_check --base-url http://nginx:8080 --expect-mode nonproduction
```

`verify_migration` должен подтвердить 95 старых страниц с HTTP 200 и 27 прежних ошибок с HTTP 404. Для просмотра staging до смены DNS можно временно сопоставить `legionautorent.kz` с новым IP в hosts на своём компьютере и открыть HTTP-версию. Отдельно проверьте главную, город, автомобиль, /contacts/ и /control-legion/, все изображения и обратную прокрутку hero на телефоне.

Существующие пользователи админки переносятся с дампом. Если нужно создать нового владельца, используйте интерактивную команду:

```sh
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py createsuperuser
```

Никогда не сохраняйте пароль владельца в README. Если нужно сбросить пароль существующего пользователя, используйте `python manage.py changepassword ИМЯ` внутри `web`.

## 5. HTTPS и домен

Чтобы получить сертификат до переключения A-записей, можно подтвердить владение через DNS, оставив старый сайт доступным. На сервере выполните интерактивно:

```sh
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm certbot certonly --manual --preferred-challenges dns -d legionautorent.kz -d www.legionautorent.kz --email YOUR_EMAIL --agree-tos
```

Certbot покажет необходимые TXT-записи. Добавьте именно показанные значения в DNS, дождитесь их доступности и только затем продолжите проверку. После выдачи:

```sh
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm --entrypoint sh certbot /opt/certificate-permissions.sh
```

В `.env.production` установите:

```dotenv
ENVIRONMENT=production
SECURE_SSL_REDIRECT=true
ANALYTICS_ENABLED=true
NGINX_CONFIG=./deploy/nginx.conf
```

Затем:

```sh
docker compose --env-file .env.production -f docker-compose.yml up -d --force-recreate web nginx
```

Перед публичным переключением проверьте HTTPS через hosts или `curl --resolve legionautorent.kz:443:SERVER_IP https://legionautorent.kz/healthz/`. После успешной проверки направьте A-записи `legionautorent.kz` и `www` на IP PS.kz. Устаревшую AAAA-запись оставляйте только если IPv6 нового сервера действительно настроен.

После обновления DNS переведите сертификат на автоматическое HTTP-подтверждение:

```sh
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm certbot certonly --webroot -w /var/www/acme --force-renewal -d legionautorent.kz -d www.legionautorent.kz --email YOUR_EMAIL --agree-tos
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm --entrypoint sh certbot /opt/certificate-permissions.sh
docker compose --env-file .env.production -f docker-compose.yml exec nginx nginx -s reload
```

Проверьте `certbot renew --dry-run` через тот же профиль. Ручной DNS-сертификат без этого перехода не обновляется автоматически.

## 6. Проверка опубликованного сайта

```sh
docker compose --env-file .env.production -f docker-compose.yml exec web python manage.py release_check --base-url https://legionautorent.kz --expect-mode production --redirect-origin http://www.legionautorent.kz
docker compose --env-file .env.production -f docker-compose.yml logs --tail=100 web nginx
```

Убедитесь, что production robots и sitemap доступны, страницы не получили staging noindex, формы создают заявки, WhatsApp открывается отдельно. Аналитика подключается только через GTM: в контейнере должны быть Метрика **92545653** и GA4 **G-00P3VJTEK9**. Проверьте события звонка, WhatsApp и заявки в режиме просмотра GTM.

## 7. Резервные копии, обновление и возврат

Ежедневная копия:

```sh
LEGION_ROOT=/srv/legion LEGION_ENV_FILE=.env.production sh deploy/backup-compose.sh
```

Добавьте команду в cron системного пользователя, имеющего доступ к Docker, и копируйте результат в отдельное защищённое хранилище. Наличие файлов на том же диске не защищает от потери сервера. Периодически проверяйте восстановление в отдельной новой установке.

Для сертификата добавьте отдельное регулярное выполнение:

```sh
cd /srv/legion
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm certbot renew --quiet
docker compose --env-file .env.production -f docker-compose.yml --profile certificate run --rm --entrypoint sh certbot /opt/certificate-permissions.sh
docker compose --env-file .env.production -f docker-compose.yml exec nginx nginx -s reload
```

Перед каждым обновлением сделайте копию и запишите текущий commit:

```sh
git rev-parse HEAD
LEGION_ROOT=/srv/legion LEGION_ENV_FILE=.env.production sh deploy/backup-compose.sh
git pull --ff-only origin main
docker compose --env-file .env.production -f docker-compose.yml build web
docker compose --env-file .env.production -f docker-compose.yml up -d --wait web nginx
```

Не запускайте повторный импорт как часть обновления: он возвращает цены и SEO к исходному снимку. Для возврата к старой версии используйте сохранённый commit в отдельном checkout и проверенную копию БД; учитывайте совместимость миграций. Не откатывайте БД поверх работающей установки без предварительного сохранения новых заявок.

## Что подтверждено локально

104 Django-теста и проверка 122 старых URL прошли локально и в Linux на GitHub. Реальная сборка Docker, запуск PostgreSQL 18, Gunicorn и Nginx, работа томов, healthz и главной страницы подтверждены в [GitHub Actions](https://github.com/AtazhanErbol/legionautorent-kz/actions/runs/37454434314) через docker-compose.dev.yml. Производственные Compose-конфигурации проверены по схеме, Nginx — по синтаксису. Выпуск и продление сертификата, cron, публичные редиректы и запуск именно на PS.kz ещё требуют проверки на конечном сервере. Доступ к PS.kz пока не предоставлен, публичный домен не переключён.
