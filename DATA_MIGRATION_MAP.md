> Исторический документ предыдущей реализации. Актуальные решения от 03.10.2026: README.md, DEPLOY.md и reports/SEO_MIGRATION_REPORT.md.

# Data migration map

Старая БД и uploads недоступны. Реализуется HTTP fallback из сохранённых исходных страниц, без обращения к закрытым интерфейсам и без отправки старых форм.

| Публичный источник | Django | Политика |
|---|---|---|
| точный URL автомобиля | Car.legacy_path | уникальный, сохраняет slash/регистр/суффиксы |
| URL slug | Car.slug / legacy_id | ID `http:<path>`; внутренний старый DB ID неизвестен |
| `.car_name`, H1 | Car.name, seo_h1 | исходные строки; Title не заменять без причины |
| `.car_price`, `.car_text` | Car.base_price | Decimal, KZT; без выдуманных тарифов |
| `.term_duration`, `.term_discount` | CarDiscount | старые интервалы пересекаются: перенос как справочные условия; новые тарифы задаются в Admin |
| `.car_item` на городах | Car.cities | M2M: автомобиль может встречаться в нескольких городах |
| первый токен имени | CarBrand | нормализация BMW, Mercedes, Toyota и прочих; исходное имя сохранено |
| категория | CarCategory | в источнике отсутствует: редакторская классификация по модели, требует проверки |
| `.car_inner_img[data-src]` | CarImage.original, legacy_url | скачать оригиналы, не thumbnails; hash по URL, повторный импорт не дублирует |
| alt, caption | CarImage.alt, caption | отсутствующий alt дополнить именем автомобиля |
| `.seo_text` | City.body | sanitize HTML; исправить чужой город и CMS-заглушки с записью в отчёте |
| title, description, h1, canonical, OG | SEOFields в Car/City/Page | сохраняются непустые поля; canonical проверяется по собственному URL |
| footer `.loc`, tel, iframe | City.address, phone, map_url | публичные заглушки не считать адресом |
| активные scripts | SiteSettings.analytics IDs | импорт без включения на staging |

Характеристики (год, коробка, привод, места), свободные даты, юридические условия и состояние реального автомобиля в старом HTML не опубликованы. Поля остаются пустыми; отсутствие не заменяется предположением.

## Повторяемость и контроль

`python manage.py migrate_legion_data --download-images` читает snapshot, использует update_or_create по legacy_path и legacy_url. Транзакции отдельных автомобилей, отдельный отчёт скачивания media, оригиналы и responsive WebP. Повторный запуск не удаляет данные; для обновления существующего контента требуется `--refresh`.

`--dry-run` проверяет структуру и выводит план без записи. JSON export adapter позволяет передать нормализованный экспорт БД через `--source`, формат совпадает с migration/normalized.json. Snapshot и оригинальные media сохраняются для обратной сверки. Удаления/автоматическое объединение похожих slug запрещены.
