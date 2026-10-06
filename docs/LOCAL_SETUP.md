# Локальный запуск

Используйте Python 3.12, Node.js 24 и PostgreSQL 18. Производственная конфигурация и перенос действующих данных описаны в [DEPLOY_PS_KZ.md](DEPLOY_PS_KZ.md).

## Без Docker

Создайте отдельную локальную базу `legion` и пользователя с правами на эту базу. Для тестов пользователь должен иметь право создавать тестовую базу. Производственному пользователю это право не выдаётся.

```sh
python -m venv .venv
```

Активируйте окружение: в Windows PowerShell — `.venv\Scripts\Activate.ps1`, в Linux/macOS — `source .venv/bin/activate`.

```sh
python -m pip install -r requirements.txt
npm ci
npm run build
```

Скопируйте `.env.example` в `.env`. Укажите собственные `SECRET_KEY` и `DATABASE_URL` для локальной PostgreSQL. Оставьте development, выключенную аналитику и `SECURE_SSL_REDIRECT=false`. `.env` не включается в Git.

Для новой пустой базы:

```sh
python manage.py migrate
python manage.py createcachetable
python manage.py configure_hero_video
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```

Если переносите текущий сайт, сначала восстановите выданный PostgreSQL dump в отдельную пустую базу и распакуйте архив медиа в папку `media/`, затем выполните миграции и сборку. Уже существующий пользователь админки будет сохранён. Импорт повторно не выполняйте.

Пустой проект может импортировать исходный каталог командой `python manage.py import_legacy --download-images`, но для точной копии текущих изменений владельца используйте восстановление базы. Это относится и к изменённым ценам, текстам, заявкам и настройкам.

Сайт: `http://127.0.0.1:8000/`. Админка: `http://127.0.0.1:8000/control-legion/`.

## Проверки

```sh
python -m pip install -r requirements-dev.txt
python tools/prepare_test_media.py
python manage.py collectstatic --noinput
python manage.py test --settings=legion.config.testing
python manage.py makemigrations --check --dry-run
npm run check:budget
python manage.py verify_migration
```

Последняя команда проверяет сохранённые URL и нуждается в восстановленной базе с каталогом. Полный HTTP-аудит сайта:

```sh
python manage.py release_check --base-url https://legionautorent.kz --expect-mode production --redirect-origin http://www.legionautorent.kz
```

До подключения домена используйте адрес проверяемой установки. Проверка публичных HTTP→HTTPS и www-редиректов завершается только после настройки DNS и HTTPS.

Для браузерной проверки запустите локальный сайт, установите движки и укажите его адрес:

```sh
python -m playwright install chromium firefox webkit
python tools/check_hero_frames.py --base-url http://127.0.0.1:8000
```

Lighthouse проверяется через `tools/audit_hero_frames.py` на loopback-адресе 8003. Для этого предусмотрен `tools/audit_server.py`; он используется только для локального измерения, никогда для публичного сервера.

## Пересобрать кадры нового ролика

Установите FFmpeg с libwebp, затем:

```sh
python tools/build_hero_frames.py --source /path/to/hero-60fps.mp4 --ffmpeg ffmpeg
python manage.py configure_hero_video
npm run build
python manage.py collectstatic --noinput
```

Готовые кадры уже включены в репозиторий. При обычном развёртывании FFmpeg не требуется. Старые кадры при следующей ручной замене удаляйте только после резервной копии и проверки нового комплекта.

В CI одноразовая база после сырого импорта получает только ранее утверждённые SEO-исправления из сохранённого manifest. `tools/prepare_ci_editorial.py` имеет отдельный защитный флаг и предназначен исключительно для одноразовой development-базы; при деплое его не запускайте. Рабочая база восстанавливается из приватной резервной копии.
