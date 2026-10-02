# Release status — 2026-10-02

**Рабочая локальная версия готова к просмотру и наполнению. Production не переключён; условия окончательного запуска ниже ещё не закрыты.**

Preview: http://127.0.0.1:8002/ · Admin: http://127.0.0.1:8002/admin/. Доступ локального admin — .local/admin-access.txt, не включён в исходники. Повторный запуск: `tools/start_dev.ps1 -OptimizedPreview`. Отдельная PostgreSQL localhost:55432; действующий сайт/его БД не менялись.

## Выполнено

- Django 5.2 LTS / PostgreSQL, CMS/Admin и роли для контента, SEO и менеджеров, server-rendered страницы, фильтры, галереи, тарифы/скидки, BookingRequest, контактные WhatsApp, first-touch UTM и event hooks.
- Перенесены **91 автомобиль, 4 города, 302 записи галерей** из публичного HTTP snapshot. **300 уникальных изображений** скачаны без пропусков, оригиналы и WebP сохранены. Импорт повторяемый, правки CMS сохраняет. Непредоставленные исходные DB IDs не выдуманы.
- **95/95 старых доступных URL сохранены точно**, включая отсутствие trailing slash у `/car/...`. Crawl: 0 broken links, 0 metadata errors. Остальные 27 legacy URL уже возвращали 500 на старом сайте.
- RU остаётся без prefix; KZ `/kz/` с `lang=kk`, EN `/en/`. Django gettext UI, отдельные CMS-переводы/SEO, публикация полного проверенного текста, эквивалентный language switcher, self canonical и reciprocal hreflang для опубликованных страниц. Неопубликованный перевод: понятный fallback, noindex, без sitemap/hreflang.
- Новое ТЗ имеет приоритет: InvestorApplication, форма/статусы/страницы инвесторам отсутствуют. Партнёрский информационный блок с точным RU текстом управляется SiteSettings; отдельные редактируемые KZ/EN поля и WhatsApp-message. До публикации их перевода блок скрыт в KZ/EN, чтобы не подставлять русское сообщение.
- Premium responsive UI, photo Hero, ленивые GSAP/Three.js/Draco и 3D fallback. Реальный 3D Hero не включён без лицензированного автомобильного GLB.
- 46 tests passed, Chrome 320–1920 px, Django deploy check чистый; Lighthouse mobile 94 performance / 100 accessibility / 100 best practices. Локальный SEO score 69 вследствие закрытого preview.
- Backup и проверенное восстановление: `legion-20261002T110827Z.dump`, `media-20261002T110827Z.tar.gz`, 1500 media files. Полный backup старого production этим не заменяется.
- Подготовлены env, lockfiles, migrations, Gunicorn/Nginx/systemd/Docker Compose, SSL/backup/deploy инструкции и SEO/data/translation reports.

## До переключения production

1. Восстановить 27 недоступных legacy cars из исходной БД либо согласовать **индивидуальные** релевантные 301. Список seo_url_migration.csv. Сейчас настоящие 404; массового redirect на главную нет.
2. Заполнить/проверить KZ/EN контент в Admin: cars, cities, categories, pages, FAQ, content blocks, SiteSettings/partner messages. Из старого источника перенесён только RU; машинный перевод не выполнялся. После публикации полных переводов sitemap/hreflang обновляются.
3. Проверить классификацию категорий и 15 групп одноимённых legacy Title/Description, указать реальные характеристики авто, условия возраста/стажа/депозита/пробега и адрес Павлодара. Не выдумывать данные для SEO.
4. Утвердить privacy/consent drafts, бизнес-тексты и действующие контакты. Заявка сохраняется в Admin; не подтверждает свободные даты или договор. Email/Telegram/CRM можно подключить после передачи настроек и отдельного поручения.
5. Предоставить лицензированный выбранный автомобильный GLB, оптимизировать/проверить его на целевых устройствах и при необходимости включить в SiteSettings. Photo fallback уже работает.
6. Проверить приватную конфигурацию существующего GTM/GA4/Метрики и событий: исключить двойной учёт и связать dataLayer events с тегами. Идентификаторы/verification сохранены; analytics локально/staging отключена.
7. Развернуть защищённый staging на целевом сервере, выполнить Docker/Nginx/SSL и restore checks. Правильно задать TRUSTED_PROXY_IPS для native или Docker peer. Измерить CWV с настоящими assets/analytics: локальный LCP 2.6 s, field INP пока неизвестен.
8. Снять полный backup действующего production, повторить сверку данных/URL перед переключением, настроить ENVIRONMENT=production/SITE_URL/SSL/analytics и проверить robots (снять staging noindex). Production switch — только после закрытия этих пунктов. Затем отправить sitemap в Search Console/Вебмастер и наблюдать реальные ошибки/индексацию.

## Документы и команды

README.md · DEPLOYMENT.md · SEO_MIGRATION_PLAN.md · DATA_MIGRATION_MAP.md · TRANSLATION_ARCHITECTURE.md · seo_migration_report.md · data_migration_report.md · translation_migration_report.md · TEST_REPORT.md · PERFORMANCE_REPORT.md · backup_report.json.

`python manage.py release_check` показывает фактические условия; `--strict` завершает команду ошибкой, пока данные/публикация/конфигурация не завершены. Локальный тест и сохранённый URL не дают гарантии сохранения позиций: необходимы проверки после реального переключения.
