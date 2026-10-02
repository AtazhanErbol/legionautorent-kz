# Performance report

Измерено 2026-10-02: локальный WSGI preview http://127.0.0.1:8002/, DEBUG=False, WhiteNoise compressed manifest assets, PostgreSQL 18.6. Production Nginx/Gunicorn не развёрнуты. Lighthouse 13.5.0, mobile simulation, simulate throttling. Аналитика и коммерческая 3D-модель отключены.

| Проверка | Результат |
|---|---:|
| Performance | 94/100 |
| Accessibility | 100/100 |
| Best practices | 100/100 |
| SEO в закрытом preview | 69/100 |
| FCP | 0.9 s |
| LCP | 2.6 s |
| CLS | 0 |
| TBT | 180 ms |

SEO score снижен намеренными robots noindex и запретом обхода staging. Полный внутренний crawl отдельно выполнен в симуляции production; локальный запрет индексации не снят.

LCP 2.6 s в этом запуске немного выше цели 2.5 s. Это лабораторный замер на Windows, без production hosting/CDN. TBT не равен INP: полевой INP и 75-й процентиль Core Web Vitals не измерены. Проверить повторно после настройки реального сервера и затем по CrUX/Search Console; гарантии поисковых позиций или field CWV не заявляются.

Hero preload/fetchpriority high, заданные размеры, локальный Golos Text WOFF2 и font-display swap. Оригиналы сохранены; галереи WebP 640/1200, карточки WebP 640/960 с нужным crop/aspect ratio, srcset/sizes и lazy loading. CSS/JS/font manifest и сжатие. Основной HTML server-rendered, работа каталога и заявки не зависит от JS. GSAP загружается в idle только на desktop. Three.js/Draco загружаются по кнопке, без 3D на mobile/reduced motion/saveData; сцена не рисуется вне viewport или скрытой вкладки.

SQL query counts после прогрева: {'/': 27, '/cars/': 22, '/car/toyota-camry-xv-70-prestige-plus': 27}. Регрессионный тест сравнивает малый и расширенный каталог, исключая рост по одной группе запросов на каждую машину.

Исходный Lighthouse JSON: output/playwright/lighthouse-mobile-final.json. Проверенный asset footprint зависит от фактического автопарка и подключённой впоследствии модели/аналитики.
