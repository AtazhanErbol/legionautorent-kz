# Test report

Дата: 2026-10-02. Проверки локальной реализации, PostgreSQL, Chrome headless.

- Django test: **46 passed**, 0 failures. URL/trailing slash, активность контента, SEO/JSON-LD, RU/KZ/EN и опубликованные переводы, взаимный hreflang, sitemap/robots, 301 без циклов и цепочек, настоящая 404, CMS/Admin, idempotent import, безопасный rich text, формы/реальный CSRF/consent/даты/телефон/honeypot/rate limit/UTM/source, партнёрский WhatsApp, отсутствие InvestorApplication routes, SQL growth, прозрачность palette PNG и производные WebP.
- `manage.py makemigrations --check --dry-run`: нет рассинхронизации моделей и миграций.
- `manage.py check --deploy` с production environment, DEBUG=False и SSL redirect: 0 замечаний. Это проверка Django settings, не проверка установленного Nginx/SSL на удалённом сервере.
- UI translations: 144 Django PO/MO strings, missing 0. Это новый интерфейс; старые бизнес-тексты автоматически не переводились.
- SEO crawl: 131 путей, 95/95 доступных старых URL сохранены; 0 broken internal links, 0 metadata/image/JSON syntax errors.
- Chrome: ширины 320, 375, 390, 430, 768, 1024, 1440, 1920 px. Нет overflow, пропавших загруженных изображений, JS/console errors; 1 H1 на главной. Каталог, автомобиль, город, форма, KZ/EN fallback: HTTP 200. Переключение языка сохраняет страницу, меню работает с Escape, галерея меняет фото.
- Three.js loader: собственный тестовый off-origin GLB загружен и виден (17616 painted pixels), фото скрывается после успеха, page errors 0. Коммерческий автомобиль/его лицензия и реальная Draco-модель этим тестом не подтверждаются.
- Финальный backup: 1500 media files; pg_restore в отдельную временную DB успешен, восстановлены 91 car / 4 city / 302 gallery associations. SHA256 в backup_report.json и manifests.

Синтаксическая JSON-LD проверка не заменяет Google Rich Results Test. Lighthouse Accessibility 100 не заменяет полный ручной WCAG audit. Production analytics/SSL/Nginx/Docker/доставка заявок во внешние системы и field INP не проверены локально. Production не переключался.

Артефакты: output/playwright/browser_report.json, hero3d_report.json, screenshots; seo_audit_new_site.json; backup_report.json; PERFORMANCE_REPORT.md.
