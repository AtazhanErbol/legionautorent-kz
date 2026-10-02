# Производительность — 03.10.2026

Lighthouse 13.5.0, мобильный профиль с simulated throttling, локальный Chrome и Nginx 1.30.5 → Django/PostgreSQL, DEBUG=False, production HTML/robots, внешняя аналитика выключена. Последние отчёты сняты 02.10.2026 22:10–22:11 UTC (03.10 по местному времени).

| Страница | Performance | Accessibility | Best Practices | SEO | LCP | CLS | TBT |
|---|---:|---:|---:|---:|---:|---:|---:|
| Главная | 98 | 100 | 100 | 100 | 2,329 с | 0,000009 | 0 мс |
| Lexus LX 570 Superior | 99 | 100 | 100 | 100 | 2,179 с | 0,000114 | 0 мс |
| Каталог | 99 | 100 | 100 | 100 | 2,103 с | 0,000071 | 0 мс |

Целевые лабораторные пороги выполнены на этих трёх страницах. Результаты — последний проход после оптимизации, не медиана независимых запусков. Локальная сеть и отсутствие внешней аналитики ограничивают переносимость результатов на production. TBT не является измерением INP: полевой INP <200 мс пока не подтверждён и проверяется после запуска в CrUX/Search Console.

Файлы: `reports/lighthouse-home.json`, `lighthouse-car.json`, `lighthouse-catalog.json`, сводка `reports/performance_summary.json`.

Что изменено: тяжёлый исходный логотип заменён в интерфейсе производной WebP-копией (оригинал сохранён); шрифты уменьшены до ~84 КБ суммарно с сохранением RU/KK/EN, Exo 2 — один используемый display weight 600; постер предзагружается до шрифтов; небольшая таблица стилей встроена в SSR HTML, чтобы убрать блокирующий запрос. Для ленивых карточек sizes=auto и AVIF/WebP выбирают фактическую ширину; исходники не удалены. Медиа имеет размеры в HTML, карты/аналитика/3D отложены, кеш контекста инвалидируется при редактировании CMS.

## Бюджеты

- Основной JS: 2 640 байт gzip.
- Three.js + сцена/GLTFLoader/OrbitControls + meshopt decoder: **149 300 байт gzip**, порог <150 000.
- GSAP/ScrollTrigger — отдельный отложенный chunk: 42 294 байта gzip; суммарно с ним ~192 КБ. Он не скрыт из отчёта, но бюджет ТЗ сформулирован для Three/сцены.
- Meshopt GLB: 13 012 байт; исходный GLB сохранён. Постер: 8 282 байта.
- На mobile <768px, Save-Data, reduced-motion и low memory 3D-модули/GLB не загружаются.

Сжатие выполняет `tools/precompress_assets.py` (Zopfli/Brotli) **после** collectstatic; обычный gzip оценщика Vite для этой библиотеки больше строгого порога. Nginx действительно отдаёт предварительно сжатые файлы: проверены br/gzip/identity/q=0 и совпадение распакованных байтов (`reports/nginx_http.json`). Отдельный motion chunk и опциональный Draco decoder обозначены в `reports/asset_budget.json`. Linux-контейнер пока не запускался.

## Воспроизведение

После build, collectstatic и precompress запустить `tools/audit_server.py` на loopback:8003 и локальный Nginx с конфигурацией, подготовленной `tools/validate_deployment.py`, на 8004. Подготовка нативного Nginx описана в этом скрипте; в production используется конфигурация из deploy/ и адрес реального staging-сервера.

```powershell
$env:CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
node node_modules/lighthouse/cli/index.js http://127.0.0.1:8004/ --chrome-flags="--headless --no-sandbox" --output=json --output-path=reports/lighthouse-home.json --quiet
```

`--no-sandbox` здесь относится к отдельному локальному автоматическому Chrome, не к web-серверу. На сервере повторить замер без конкурирующих задач, с реальным TLS и production analytics. Проверить главную, город, тяжёлую карточку и каталог на реальном телефоне; затем наблюдать полевые CWV. Замена GLB, добавление скриптов или новых шрифтов требует повторной проверки бюджета.
