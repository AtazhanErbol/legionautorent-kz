# Legion Auto Rent

Новая серверная версия сайта на Django 5.2 LTS и PostgreSQL, созданная отдельно от действующего production. Старые русские URL сохранены. KZ — `/kz/` с кодом `kk`, EN — `/en/`. Формы сохраняют заявки менеджеру, без онлайн-оплаты и realtime availability.

## Локальный просмотр

```powershell
.\tools\start_dev.ps1
```

Сайт: http://127.0.0.1:8000/ · Admin: http://127.0.0.1:8000/admin/.

Для просмотра с компрессией и manifest static: `.\tools\start_dev.ps1 -OptimizedPreview`. Сайт и admin будут на http://127.0.0.1:8002/. Оба режима используют изолированную PostgreSQL на порту 55432 и запрещают индексацию. OptimizedPreview служит для локальной проверки, production запускается через Gunicorn/Nginx по DEPLOYMENT.md.

Созданный локальный admin доступ находится в `.local/admin-access.txt` (игнорируется Git). Для нового окружения: `python manage.py createsuperuser`.

## Архитектура

core — настройки, контент, локализация, шаблоны; cars — каталог/изображения/тарифы/скидки; locations — города; pages — CMS/FAQ; bookings — заявки и антиспам; seo — переводы, canonical, redirects и sitemap; analytics — attribution. Партнёрский блок управляется SiteSettings и переводами, без формы и отдельной страницы.

Admin позволяет редактировать машины, города, классы, фото/порядок/alt, цены, тарифы, SEO, страницы, FAQ, преимущества/условия, настройки партнёрства и заявки. KZ/EN inline sections содержат отдельные поля и публикацию. Для новых автомобилей URL/legacy ID создаются автоматически; импортированные пути при редактировании не меняются.

## Импорт и проверки

```powershell
.\.venv\Scripts\python.exe manage.py migrate_legion_data --dry-run
.\.venv\Scripts\python.exe manage.py migrate_legion_data
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe tools\audit_new.py
.\.venv\Scripts\python.exe tools\browser_smoke.py
```

Повторный импорт не создаёт дубли и не перезаписывает редакторские правки. `--refresh` — только осознанное обновление после backup. `tools/crawl_legacy.py` обновляет HTTP snapshot, `tools/normalize_legacy.py` готовит map, `--download-images` переносит originals/WebP. Старый production читается, формы туда не отправляются.

Assets уже сохранены. Для обновления vendor: `npm ci` → `npm run vendor`. Для сборки интерфейсных PO/MO: requirements-dev.txt и `python tools/build_messages.py`.

## Документы

- SEO_MIGRATION_PLAN.md, seo_audit_old_site.csv/json, seo_url_migration.csv.
- DATA_MIGRATION_MAP.md, data_migration_report.md/json и media manifest.
- TRANSLATION_ARCHITECTURE.md, translation_migration_report.md.
- seo_migration_report.md, seo_audit_new_site.json, seo_content_differences.csv.
- DEPLOYMENT.md, deploy/ и backup_report.json.
- RELEASE_STATUS.md — фактический статус и оставшиеся release gates.
- TEST_REPORT.md и PERFORMANCE_REPORT.md — результаты проверок и ограничения локальных измерений.

Не объявлять production выпущенным по одному локальному preview: старые 500, переводы, юридические drafts, реальные характеристики/условия, лицензированная GLB и analytics configuration требуют отдельного закрытия. Автоматический перевод старых текстов не выполняется; fallback понятен пользователю и не индексируется.
