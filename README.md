# Legion Auto Rent — текущая версия

Локальный просмотр: http://127.0.0.1:8002/. Первый ролик Mercedes утверждён владельцем; визуальные решения затем переданы агенту. Сайт сохраняет Django, PostgreSQL, импорт, заявки и существующие адреса.

Актуальное состояние и ограничения: **[FINAL_PROJECT_REPORT](reports/FINAL_PROJECT_REPORT.md)**. Инструкция запуска: **[DEPLOY](DEPLOY.md)**. Лабораторные измерения: **[PERFORMANCE_REPORT](PERFORMANCE_REPORT.md)**. Результат проверки перед публикацией: **[prelaunch_report](reports/prelaunch_report.md)**.

## Что работает

- Общий тёмный дизайн всех страниц RU/KK/EN; 91 машина в серверном HTML каталога, 12 карточек видимы сразу, остальные раскрываются без запроса.
- Утверждённый Mercedes: нативная прокрутка в обе стороны, без автоматического проигрывания на desktop. Полный кадр без обрезки, статические режимы для телефона, низкого экрана, слабого устройства и reduced-motion. Кнопка ручного просмотра на узких экранах.
- Галереи, поиск, категории, сортировка, формы с CSRF, телефон и WhatsApp, FAQ, мобильная панель контактов.
- Site Settings: локальные пути видео/постеров, флаг анимации и подписи RU/KK/EN. H1 остаётся SEO-полем города. Старые 3D-данные сохранены, но не используются и не поставляются в Docker.
- Только GTM; GA4/Метрика напрямую не внедряются. Их наличие проверяет владелец внутри контейнера.

## Шрифты

Самостоятельно размещённые Montserrat 600 (57 336 байт) и Golos Text 400–600 (43 160 байт), WOFF2, font-display: swap. Проверка fontTools: `Ә Ғ Қ Ң Ө Ұ Ү Һ І ә ғ қ ң ө ұ ү һ і` и `₸` присутствуют в обоих файлах; пропусков нет. Доказательство: `reports/night_fonts.json`. Две семьи в активной сборке; прежние файлы не используются.

## Запуск и проверка

```powershell
.venv\Scripts\python.exe -X utf8 manage.py migrate
.venv\Scripts\python.exe -X utf8 manage.py configure_hero_video
npm run build
.venv\Scripts\python.exe -X utf8 manage.py collectstatic --noinput
.venv\Scripts\python.exe -X utf8 tools/preview_server.py
```

Секреты и подключение к БД — в локальном `.env`, который не входит в Git. Локальная PostgreSQL работает на 127.0.0.1:55432. `tools/preview_server.py` всегда закрыт от индексации; не используйте его как production-сервер.

```sh
python manage.py test --settings=legion.config.testing --keepdb --noinput
python manage.py verify_migration
python manage.py release_check --base-url https://legionautorent.kz
```

`make seo-test` и `scripts/prelaunch.sh` объединяют повторяемые проверки. Docker-команды, создание администратора, восстановление данных и откат подробно описаны в DEPLOY.md. Автоматический импорт при старте отключён.

## Сохранённые источники

Снимки старого сайта и реестр URL: `migration/`; загруженные фотографии: `media/`; исходные референсы: `design_refs/` и `review/mercedes-reference-originals/`. Резервные копии: `backups/`, последний проверенный manifest перед завершением — `20261003T223851Z`. GLB/эксперименты остаются локально; Docker исключает их, `review/` и резервные копии. Ни файлы исходных данных, ни записи каталога не удалялись.

## Перед публикацией

Проверка выпуска намеренно остаётся красной из-за защищённых дублей SEO и непроверенного внешнего редиректа. Не обходите её ради тега. План действий владельца — `reports/POST_LAUNCH_CHECKLIST.md`. Исторические отчёты относятся к указанным в них этапам, а не к текущей сборке.
