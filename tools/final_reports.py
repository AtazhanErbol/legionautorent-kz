"""Summarize verified local evidence; never assert a production release or field CWV."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
read=lambda name:json.loads((root/name).read_text(encoding='utf8'))
lh=read('output/playwright/lighthouse-mobile-final.json')
browser=read('output/playwright/browser_report.json')
seo=read('seo_audit_new_site.json')
backup=read('backup_report.json')
hero=read('output/playwright/hero3d_report.json')
scores={name:round(value['score']*100) for name,value in lh['categories'].items()}
audits=lh['audits']
metric=lambda name:audits[name]['displayValue']
performance=f'''# Performance report

Измерено 2026-10-02: локальный WSGI preview http://127.0.0.1:8002/, DEBUG=False, WhiteNoise compressed manifest assets, PostgreSQL 18.6. Production Nginx/Gunicorn не развёрнуты. Lighthouse {lh['lighthouseVersion']}, mobile simulation, {lh['configSettings']['throttlingMethod']} throttling. Аналитика и коммерческая 3D-модель отключены.

| Проверка | Результат |
|---|---:|
| Performance | {scores['performance']}/100 |
| Accessibility | {scores['accessibility']}/100 |
| Best practices | {scores['best-practices']}/100 |
| SEO в закрытом preview | {scores['seo']}/100 |
| FCP | {metric('first-contentful-paint')} |
| LCP | {metric('largest-contentful-paint')} |
| CLS | {metric('cumulative-layout-shift')} |
| TBT | {metric('total-blocking-time')} |

SEO score снижен намеренными robots noindex и запретом обхода staging. Полный внутренний crawl отдельно выполнен в симуляции production; локальный запрет индексации не снят.

LCP {metric('largest-contentful-paint')} в этом запуске немного выше цели 2.5 s. Это лабораторный замер на Windows, без production hosting/CDN. TBT не равен INP: полевой INP и 75-й процентиль Core Web Vitals не измерены. Проверить повторно после настройки реального сервера и затем по CrUX/Search Console; гарантии поисковых позиций или field CWV не заявляются.

Hero preload/fetchpriority high, заданные размеры, локальный Golos Text WOFF2 и font-display swap. Оригиналы сохранены; галереи WebP 640/1200, карточки WebP 640/960 с нужным crop/aspect ratio, srcset/sizes и lazy loading. CSS/JS/font manifest и сжатие. Основной HTML server-rendered, работа каталога и заявки не зависит от JS. GSAP загружается в idle только на desktop. Three.js/Draco загружаются по кнопке, без 3D на mobile/reduced motion/saveData; сцена не рисуется вне viewport или скрытой вкладки.

SQL query counts после прогрева: {seo['query_counts']}. Регрессионный тест сравнивает малый и расширенный каталог, исключая рост по одной группе запросов на каждую машину.

Исходный Lighthouse JSON: output/playwright/lighthouse-mobile-final.json. Проверенный asset footprint зависит от фактического автопарка и подключённой впоследствии модели/аналитики.
'''
(root/'PERFORMANCE_REPORT.md').write_text(performance,encoding='utf8')
tests=f'''# Test report

Дата: 2026-10-02. Проверки локальной реализации, PostgreSQL, Chrome headless.

- Django test: **46 passed**, 0 failures. URL/trailing slash, активность контента, SEO/JSON-LD, RU/KZ/EN и опубликованные переводы, взаимный hreflang, sitemap/robots, 301 без циклов и цепочек, настоящая 404, CMS/Admin, idempotent import, безопасный rich text, формы/реальный CSRF/consent/даты/телефон/honeypot/rate limit/UTM/source, партнёрский WhatsApp, отсутствие InvestorApplication routes, SQL growth, прозрачность palette PNG и производные WebP.
- `manage.py makemigrations --check --dry-run`: нет рассинхронизации моделей и миграций.
- `manage.py check --deploy` с production environment, DEBUG=False и SSL redirect: 0 замечаний. Это проверка Django settings, не проверка установленного Nginx/SSL на удалённом сервере.
- UI translations: 144 Django PO/MO strings, missing 0. Это новый интерфейс; старые бизнес-тексты автоматически не переводились.
- SEO crawl: {len(seo['pages'])} путей, {seo['preserved_successful_urls']}/95 доступных старых URL сохранены; {len(seo['broken_links'])} broken internal links, {sum(len(page['errors']) for page in seo['pages'])} metadata/image/JSON syntax errors.
- Chrome: ширины {', '.join(str(v['width']) for v in browser['viewports'])} px. Нет overflow, пропавших загруженных изображений, JS/console errors; 1 H1 на главной. Каталог, автомобиль, город, форма, KZ/EN fallback: HTTP 200. Переключение языка сохраняет страницу, меню работает с Escape, галерея меняет фото.
- Three.js loader: собственный тестовый off-origin GLB загружен и виден ({hero['off_origin_model']['painted_pixels']} painted pixels), фото скрывается после успеха, page errors 0. Коммерческий автомобиль/его лицензия и реальная Draco-модель этим тестом не подтверждаются.
- Финальный backup: {backup['media_files']} media files; pg_restore в отдельную временную DB успешен, восстановлены 91 car / 4 city / 302 gallery associations. SHA256 в backup_report.json и manifests.

Синтаксическая JSON-LD проверка не заменяет Google Rich Results Test. Lighthouse Accessibility 100 не заменяет полный ручной WCAG audit. Production analytics/SSL/Nginx/Docker/доставка заявок во внешние системы и field INP не проверены локально. Production не переключался.

Артефакты: output/playwright/browser_report.json, hero3d_report.json, screenshots; seo_audit_new_site.json; backup_report.json; PERFORMANCE_REPORT.md.
'''
(root/'TEST_REPORT.md').write_text(tests,encoding='utf8')
status=f'''# Release status — 2026-10-02

**Рабочая локальная версия готова к просмотру и наполнению. Production не переключён; условия окончательного запуска ниже ещё не закрыты.**

Preview: http://127.0.0.1:8002/ · Admin: http://127.0.0.1:8002/admin/. Доступ локального admin — .local/admin-access.txt, не включён в исходники. Повторный запуск: `tools/start_dev.ps1 -OptimizedPreview`. Отдельная PostgreSQL localhost:55432; действующий сайт/его БД не менялись.

## Выполнено

- Django 5.2 LTS / PostgreSQL, CMS/Admin и роли для контента, SEO и менеджеров, server-rendered страницы, фильтры, галереи, тарифы/скидки, BookingRequest, контактные WhatsApp, first-touch UTM и event hooks.
- Перенесены **91 автомобиль, 4 города, 302 записи галерей** из публичного HTTP snapshot. **300 уникальных изображений** скачаны без пропусков, оригиналы и WebP сохранены. Импорт повторяемый, правки CMS сохраняет. Непредоставленные исходные DB IDs не выдуманы.
- **95/95 старых доступных URL сохранены точно**, включая отсутствие trailing slash у `/car/...`. Crawl: 0 broken links, 0 metadata errors. Остальные 27 legacy URL уже возвращали 500 на старом сайте.
- RU остаётся без prefix; KZ `/kz/` с `lang=kk`, EN `/en/`. Django gettext UI, отдельные CMS-переводы/SEO, публикация полного проверенного текста, эквивалентный language switcher, self canonical и reciprocal hreflang для опубликованных страниц. Неопубликованный перевод: понятный fallback, noindex, без sitemap/hreflang.
- Новое ТЗ имеет приоритет: InvestorApplication, форма/статусы/страницы инвесторам отсутствуют. Партнёрский информационный блок с точным RU текстом управляется SiteSettings; отдельные редактируемые KZ/EN поля и WhatsApp-message. До публикации их перевода блок скрыт в KZ/EN, чтобы не подставлять русское сообщение.
- Premium responsive UI, photo Hero, ленивые GSAP/Three.js/Draco и 3D fallback. Реальный 3D Hero не включён без лицензированного автомобильного GLB.
- 46 tests passed, Chrome 320–1920 px, Django deploy check чистый; Lighthouse mobile {scores['performance']} performance / 100 accessibility / 100 best practices. Локальный SEO score {scores['seo']} вследствие закрытого preview.
- Backup и проверенное восстановление: `{backup['database']}`, `{backup['media']}`, {backup['media_files']} media files. Полный backup старого production этим не заменяется.
- Подготовлены env, lockfiles, migrations, Gunicorn/Nginx/systemd/Docker Compose, SSL/backup/deploy инструкции и SEO/data/translation reports.

## До переключения production

1. Восстановить 27 недоступных legacy cars из исходной БД либо согласовать **индивидуальные** релевантные 301. Список seo_url_migration.csv. Сейчас настоящие 404; массового redirect на главную нет.
2. Заполнить/проверить KZ/EN контент в Admin: cars, cities, categories, pages, FAQ, content blocks, SiteSettings/partner messages. Из старого источника перенесён только RU; машинный перевод не выполнялся. После публикации полных переводов sitemap/hreflang обновляются.
3. Проверить классификацию категорий и 15 групп одноимённых legacy Title/Description, указать реальные характеристики авто, условия возраста/стажа/депозита/пробега и адрес Павлодара. Не выдумывать данные для SEO.
4. Утвердить privacy/consent drafts, бизнес-тексты и действующие контакты. Заявка сохраняется в Admin; не подтверждает свободные даты или договор. Email/Telegram/CRM можно подключить после передачи настроек и отдельного поручения.
5. Предоставить лицензированный выбранный автомобильный GLB, оптимизировать/проверить его на целевых устройствах и при необходимости включить в SiteSettings. Photo fallback уже работает.
6. Проверить приватную конфигурацию существующего GTM/GA4/Метрики и событий: исключить двойной учёт и связать dataLayer events с тегами. Идентификаторы/verification сохранены; analytics локально/staging отключена.
7. Развернуть защищённый staging на целевом сервере, выполнить Docker/Nginx/SSL и restore checks. Правильно задать TRUSTED_PROXY_IPS для native или Docker peer. Измерить CWV с настоящими assets/analytics: локальный LCP {metric('largest-contentful-paint')}, field INP пока неизвестен.
8. Снять полный backup действующего production, повторить сверку данных/URL перед переключением, настроить ENVIRONMENT=production/SITE_URL/SSL/analytics и проверить robots (снять staging noindex). Production switch — только после закрытия этих пунктов. Затем отправить sitemap в Search Console/Вебмастер и наблюдать реальные ошибки/индексацию.

## Документы и команды

README.md · DEPLOYMENT.md · SEO_MIGRATION_PLAN.md · DATA_MIGRATION_MAP.md · TRANSLATION_ARCHITECTURE.md · seo_migration_report.md · data_migration_report.md · translation_migration_report.md · TEST_REPORT.md · PERFORMANCE_REPORT.md · backup_report.json.

`python manage.py release_check` показывает фактические условия; `--strict` завершает команду ошибкой, пока данные/публикация/конфигурация не завершены. Локальный тест и сохранённый URL не дают гарантии сохранения позиций: необходимы проверки после реального переключения.
'''
(root/'RELEASE_STATUS.md').write_text(status,encoding='utf8')
data_path=root/'data_migration_report.md'
data=data_path.read_text(encoding='utf8')
note='Карточки дополнительно используют WebP 640/960 с оптимизированным кадрированием; всего сохранено 1500 media files (300 originals и 4 производных на каждый источник).'
if note not in data:data_path.write_text(data+'\n'+note+'\n',encoding='utf8')
print(json.dumps({'reports':['RELEASE_STATUS.md','TEST_REPORT.md','PERFORMANCE_REPORT.md'],'lighthouse':scores,'backup_restore_verified':backup['restore_verified']}))
