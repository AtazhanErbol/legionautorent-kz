# Подготовка Legion Auto Rent к PythonAnywhere

Проект подготовлен к переносу; **публикация пока не выполнялась**. Сначала владелец передаст баги, затем исправления проверяются и собирается свежий пакет. Локальная админка: `http://127.0.0.1:8002/control-legion/`.

## Требования хостинга

- Платный аккаунт для собственного домена и PostgreSQL: PostgreSQL-дополнение PythonAnywhere или внешняя PostgreSQL. [Официальная справка](https://help.pythonanywhere.com/pages/Postgres/).
- Python 3.12 или совместимая с закреплёнными зависимостями версия, одинаковая в Web app и virtualenv. PostgreSQL 14+ для Django 5.2. Параметры сервера и доступные версии проверяются в аккаунте перед переносом.
- Достаточно диска для media, кода, собранной статики и резервных копий. Размер готового пакета фиксируется при упаковке.
- Используется **Manual Configuration → WSGI**. Веб-сервер и TLS предоставляет PythonAnywhere; локальные Docker/Nginx/Certbot-файлы сохраняются как альтернативный вариант развёртывания. [Инструкция Django](https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/).

## 1. Подготовить актуальные файлы локально

После исправления багов запустить полный набор тестов, `verify_migration`, сборку `npm run build`, `collectstatic`, затем:

```powershell
.venv\Scripts\python.exe -X utf8 manage.py export_pythonanywhere --output backups/pythonanywhere-YYYYMMDD/content.json
.venv\Scripts\python.exe -X utf8 manage.py import_pythonanywhere backups/pythonanywhere-YYYYMMDD/content.json
.venv\Scripts\python.exe -X utf8 tools/package_pythonanywhere.py --output backups/pythonanywhere-YYYYMMDD/source.tar.gz
```

`import_pythonanywhere` без `--apply` лишь сверяет SHA256 и состав. Экспорт содержит автомобили, города, переводы, тексты, настройки и заявки; **не содержит локальных пользователей, паролей, сессий и попыток входа**. JSON и его `.manifest.json` передаются вместе, приватно. Media берётся из свежей проверенной резервной копии `media-TIMESTAMP.tar.gz`, вместе с manifest и дампом. `deploy/verify_backup.py` проверяет контрольные суммы и безопасные имена архива. Не размещать backups, `.env` и исходные дампы в Static Files.

Локальный PostgreSQL — 18. Не восстанавливайте его custom dump в неизвестную более старую версию. Для такого переноса предусмотрен Django JSON: схема создаётся миграциями на целевой версии, затем загружаются данные. Полный pg_dump остаётся резервной копией.

## 2. Создать окружение в Bash Console хостинга

Распаковать исходники в `/home/YOUR_USERNAME/legionautorent.kz`, подставляя свой username во всех путях. Не переносить Windows `.venv`, `.local` или локальную `.env`.

```bash
cd /home/YOUR_USERNAME/legionautorent.kz
mkvirtualenv --python=/usr/bin/python3.12 legion
pip install -r requirements.lock
cp .env.pythonanywhere.example .env.pythonanywhere
chmod 600 .env.pythonanywhere
```

В `.env.pythonanywhere` заполнить SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS и CSRF_TRUSTED_ORIGINS. Пароль внутри DATABASE_URL должен быть URL-encoded. Сгенерировать новый секрет локально в Python (`secrets.token_urlsafe(64)`) и сохранить в приватном env. На первом этапе: `ENVIRONMENT=staging`, `ANALYTICS_ENABLED=false`, `CANONICAL_HOST_REDIRECT=false`.

В console-сессии перед командами:

```bash
export LEGION_ENV_FILE=/home/YOUR_USERNAME/legionautorent.kz/.env.pythonanywhere
python manage.py check
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py import_pythonanywhere /home/YOUR_USERNAME/private-transfer/content.json
python manage.py import_pythonanywhere /home/YOUR_USERNAME/private-transfer/content.json --apply
python manage.py setup_roles
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

Импорт откажется менять базу, в которой уже есть автомобили, города, страницы или заявки. Создайте новую пустую БД для переноса. Сохранённые копии не удаляются. На production создаётся новый администратор; локальные реквизиты не используются. После переноса **не запускать `import_legacy`, `seed_rebuild` или `configure_hero_video` без отдельной причины**: они могут вернуть исходные значения поверх редакторских настроек.

Распаковать проверенный media-архив в новую пустую папку проекта. Восстановление поверх рабочего media не выполнять. Если используется готовый архив source, в нём уже есть `static/build` и manifest Vite; Node на хостинге для первого запуска не нужен.

## 3. Web app и статика

Web → Add a new web app → Manual configuration. Указать:

| Поле | Значение |
|---|---|
| Source / Working directory | `/home/YOUR_USERNAME/legionautorent.kz` |
| Virtualenv | `/home/YOUR_USERNAME/.virtualenvs/legion` |
| WSGI configuration file | Вставить `deploy/pythonanywhere_wsgi.py`, заменив YOUR_USERNAME |
| Static Files `/static/` | `/home/YOUR_USERNAME/legionautorent.kz/staticfiles` |
| Static Files `/media/` | `/home/YOUR_USERNAME/legionautorent.kz/media` |

[Статика и media](https://help.pythonanywhere.com/pages/DjangoStaticFiles/), [env в WSGI](https://help.pythonanywhere.com/pages/environment-variables-for-web-apps/). WSGI читает отдельный `.env.pythonanywhere` до загрузки Django; не запускает миграции или импорт при каждом запросе. Для staging включить Password protection в Web tab, если доступна в тарифе. Нажать Reload и проверить журнал ошибок.

Включить HTTPS для временного домена до проверки `SECURE_SSL_REDIRECT=true`. На PythonAnywhere используется документированный `X-Real-IP`, который заменяет балансировщик; произвольный первый элемент `X-Forwarded-For` не принимается. [Источник](https://help.pythonanywhere.com/pages/WebAppClientIPAddresses).

## 4. Проверки до переключения домена

- Вход/выход из админки, ограниченная роль менеджера, сохранение цены, текста, перевода и загрузка фотографии/постера. Проверить фактическое появление изменений на сайте.
- 91 автомобиль, 4 города, 302 исходные связи изображений; заявки и последние CMS-правки сохранены. Точное актуальное число — в manifest экспорта.
- `python manage.py verify_migration`, затем HTTP-аудит staging (`release_check --base-url https://YOUR_USERNAME.pythonanywhere.com --expect-mode nonproduction`).
- `/robots.txt` запрещает индексацию staging; заголовки и meta содержат noindex. Собственные canonical по-прежнему указывают на `https://legionautorent.kz`.
- MP4 возвращает правильный Content-Type, диапазонный запрос — 206; фон не обрезан, прогресс и конец анимации работают. Реальный iPhone/Safari проверяется отдельно от Playwright WebKit.
- Формы сохраняют реальные тестовые заявки, разрешённые владельцем; связать дальнейшие уведомления с выбранным каналом отдельно. Существующий флаг notifications не подключает почтовый сервис сам по себе.

## 5. Публикация — после исправления багов

Подключить собственный домен и TLS по подсказкам Web tab, не угадывая CNAME. Выбрать основной `legionautorent.kz`; для `www` также нужна работающая HTTPS-привязка к этой же WSGI-установке. Затем `ENVIRONMENT=production`, `CANONICAL_HOST_REDIRECT=true`, `ANALYTICS_ENABLED=true`, Reload. Удалить password protection с публичного сайта. Проверить, что canonical/HTTPS дают ровно один переход с http и www, включая глубокие URL. Новая middleware готова, но внешняя цепочка проверяется только после DNS/TLS.

Запустить `release_check --base-url https://legionautorent.kz --redirect-origin https://legionautorent.kz`, повторить Lighthouse и формы. В GTM проверить наличие Метрики **92545653** и GA4 **G-00P3VJTEK9**; отдельно сайт их не вставляет. Локальный тест не подтверждает содержимое GTM-контейнера.

## 6. Резервирование и откат

В Tasks назначить ежедневный запуск:

```bash
/home/YOUR_USERNAME/.virtualenvs/legion/bin/python /home/YOUR_USERNAME/legionautorent.kz/deploy/pythonanywhere_backup.py
```

Проверить доступность совместимого `pg_dump`; при необходимости указать `PG_DUMP` полным путём. Скрипт создаёт новую папку с дампом БД, архивом media и SHA256, ничего автоматически не удаляет. После первого запуска проверить восстановление в отдельной пустой БД и папке. Хранить копию вне хостинга; следить за квотой, политика удаления в код не добавлена.

Для отката сохранить предыдущий release и env, восстановить проверенные БД/media в отдельную установку, переключить WSGI-путь/настройки подключения и Reload. Не накатывать старый дамп поверх рабочей базы.

## Что здесь ещё не проверено

Настоящий аккаунт PythonAnywhere, его тариф, версия PostgreSQL, установка Linux wheels, WSGI/reload, квота, static Range/cache, Tasks, DNS и сертификаты. Локальные проверки конфигурации не выдаются за деплой. Docker-контейнеры здесь не запускались; для выбранного хостинга они не нужны.

## Готовый локальный пакет от 05.10.2026

Актуальная папка: `backups/pythonanywhere-20261005-release/`. Использовать **source.tar.gz**, `content.json` и соответствующие manifest. Предыдущие пакеты в папках `-cms` и `-final` сохранены, но не содержат последних изменений. Media: `backups/media-20261005T122038Z.tar.gz`; проверенный полный дамп: `backups/legion-20261005T122038Z.dump`.

Финальный JSON проверен импортом в отдельную пустую локальную PostgreSQL: 91 авто, 302 связи фотографий, 4 города, 136 фраз интерфейса, 8 секций, 7 ссылок меню, 1 существующая заявка и **0 пользователей**. Проверочная база сохранена. Проверка production-настроек Django не выявила замечаний. Реальный аккаунт PythonAnywhere пока не настраивался; перенос и переключение домена не выполнялись.
