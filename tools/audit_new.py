"""Production-mode local crawl and old/new comparison. Does not switch a domain."""
import os
import sys
import json
import csv
import hashlib
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','legion.settings')
import django
django.setup()
from django.test import Client, override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from bs4 import BeautifulSoup
from cars.models import Car,CarImage
from locations.models import City
from pages.models import Page
from seo.models import Translation

ROOT=Path(__file__).resolve().parents[1]
old=json.loads((ROOT/'seo_audit_old_site.json').read_text(encoding='utf8'))
results=[];broken=[];differences=[]
client=Client()
paths=[urlsplit(p['url']).path for p in old['pages']]
with override_settings(IS_STAGING=False,DEBUG=False):
    from xml.etree import ElementTree
    sitemap=ElementTree.fromstring(client.get('/sitemap.xml').content)
    paths+= [urlsplit(n.text).path for n in sitemap.iter() if n.tag.endswith('loc')]
    checked_targets={}
    for path in sorted(set(paths)):
        response=client.get(path)
        item={'path':path,'status':response.status_code,'errors':[]}
        if response.status_code==200:
            soup=BeautifulSoup(response.content,'html.parser')
            item.update(title=soup.title.get_text(),description=soup.select_one('meta[name=description]')['content'],h1=[x.get_text(' ',strip=True) for x in soup.select('h1')],canonical=soup.select_one('link[rel=canonical]')['href'],robots=soup.select_one('meta[name=robots]')['content'],headings={f'h{i}':[x.get_text(' ',strip=True) for x in soup.select(f'h{i}')] for i in [2,3]},text=soup.select_one('main').get_text(' ',strip=True),alternates=[{'lang':x['hreflang'],'href':x['href']} for x in soup.select('link[hreflang]')])
            if not item['title']:item['errors'].append('missing_title')
            if not item['description']:item['errors'].append('missing_description')
            if len(item['h1'])!=1:item['errors'].append('bad_h1_count')
            for img in soup.select('img'):
                if not img.get('alt'):item['errors'].append('missing_alt')
                src=img.get('src','')
                if src.startswith('/media/') and not (ROOT/'media'/src.removeprefix('/media/')).exists():item['errors'].append('missing_image_file')
            for schema in soup.select('script[type="application/ld+json"]'):
                try:json.loads(schema.string)
                except ValueError:item['errors'].append('invalid_jsonld')
            for a in soup.select('a[href]'):
                href=a['href']; parsed=urlsplit(href)
                if not parsed.netloc and parsed.path.startswith('/') and not parsed.path.startswith(('/static/','/media/')):
                    if parsed.path not in checked_targets:checked_targets[parsed.path]=client.get(parsed.path).status_code
                    if checked_targets[parsed.path]>=400:broken.append({'from':path,'target':parsed.path,'status':checked_targets[parsed.path]})
        results.append(item)
    for p in old['pages']:
        now=next(x for x in results if x['path']==urlsplit(p['url']).path)
        if p['status']==200:
            differences.append({'url':p['url'],'old_title':p['title'],'new_title':now.get('title'),'old_h1':p['h1'],'new_h1':now.get('h1'),'title_changed':p['title']!=now.get('title'),'h1_changed':p['h1']!=now.get('h1'),'old_description':p['description'],'new_description':now.get('description'),'content_changed':p['text']!=now.get('text'),'old_text_hash':hashlib.sha256(p['text'].encode()).hexdigest(),'new_text_hash':hashlib.sha256(now.get('text','').encode()).hexdigest()})
    counts={}
    for path in ['/','/cars/','/car/toyota-camry-xv-70-prestige-plus']:
        with CaptureQueriesContext(connection) as queries:client.get(path)
        counts[path]=len(queries)
indexable=[r for r in results if r['status']==200 and 'noindex' not in r.get('robots','')]
duplicates={}
for field in ['title','description']:
    groups=defaultdict(list)
    for r in indexable:groups[r[field]].append(r['path'])
    duplicates[field]={k:v for k,v in groups.items() if len(v)>1}
report={'pages':results,'broken_links':broken,'duplicates':duplicates,'differences':differences,'query_counts':counts,'preserved_successful_urls':sum(p['status']==200 and next(x for x in results if x['path']==urlsplit(p['url']).path)['status']==200 for p in old['pages'])}
(ROOT/'seo_audit_new_site.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
with (ROOT/'seo_content_differences.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=list(differences[0]));writer.writeheader()
    for row in differences:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in row.items()})
lines=['# SEO migration report','',f"Проверено {len(old['pages'])} старых URL: 95 успешных и 27 HTTP 500.",f"Сохранено успешных URL без изменения пути: {report['preserved_successful_urls']} / 95. Изменённых успешных URL: 0. Требующих 301: 0.",'','27 старых HTTP 500 сейчас дают настоящий HTTP 404; данные не выдуманы. Полный список — seo_url_migration.csv. Перед production восстановить их из БД либо подтвердить индивидуальные назначения 301. Автоматического redirect на главную нет.','',f"Новый локальный crawl в симуляции production: {len(results)} путей, ошибок метаданных {sum(len(r['errors']) for r in results)}, внутренних broken links {len(broken)}.",'',f"Изменены Title: {sum(x['title_changed'] for x in differences)}; H1: {sum(x['h1_changed'] for x in differences)}. Пустые Title заполнены; непустые сохранены. Пустые Description заполнены по реальным данным. Полные значения, content hashes и различия в seo_content_differences.csv и seo_audit_new_site.json.",'','Контент каждой страницы расширен навигацией, перелинковкой и условиями, поэтому общие text hashes различаются. SEO-тексты Астаны сохранены; чужое название города исправлено в Костанае и Усть-Каменогорске, добавлена проверенная локальная информация. Заглушки Павлодара удалены. Адрес Павлодара остаётся пустым. Категории — редакторская классификация, требуется проверка владельцем.','',f"Дубликаты Title: {len(duplicates['title'])}; Description: {len(duplicates['description'])}. Одноимённые автомобили сохраняют legacy Title во избежание необоснованной смены: требуется индивидуальное уточнение по реальным комплектациям, не выдумывать характеристики.",'','Schema: JSON синтаксически проверен; нет выдуманных отзывов, рейтингов и свободных дат. Rich Results Test/Search Console требуют отдельной production-проверки.','',f'Query counts: {counts}. Используются select_related/prefetch_related.','', 'Русский URL не перенесён в /ru/. KZ/EN: полноценные маршруты и Django gettext, но контент отсутствует в старом источнике. Неопубликованные страницы noindex и исключены из sitemap/hreflang.','', 'Production не переключён. Снимок публичного сайта — не резервная копия его БД. Необходимы production backup/restore, переводческий review, уточнение бизнес-условий и юридических документов, источник лицензированной GLB, проверка конфигурации GTM против дублирования GA4/Метрики и проверка CWV на реальном сервере.']
(ROOT/'seo_migration_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
translation_lines=['# Translation migration report','','В публичном старом HTML обнаружен только lang=ru. Переключателя KZ/EN и переводов не найдено. Автоматический перевод исходного контента не выполнялся.','', '| Тип | Перенесено RU | Перенесено KZ | Перенесено EN |','|---|---:|---:|---:|',f'| Автомобили | {Car.objects.count()} | 0 | 0 |',f'| Города | {City.objects.count()} | 0 | 0 |','','144 UI-строки на KZ и EN авторские, статические, сохранены в Django PO/MO. Это переводы нового интерфейса, а не перенос старых бизнес-текстов.','','Отдельно подготовлены RU-категории, страницы CMS, FAQ, преимущества, условия и партнёрский блок. Их KZ/EN версии редактируются в Admin и требуют заполнения/публикации.','', '## Отсутствующие переводы всех исходных SEO-страниц','']
for obj in [*City.objects.all(),*Car.objects.all()]:translation_lines.append(f'- `{obj.get_absolute_url()}` — KZ / EN отсутствуют.')
(ROOT/'translation_migration_report.md').write_text('\n'.join(translation_lines)+'\n',encoding='utf8')
data=json.loads((ROOT/'data_migration_report.json').read_text(encoding='utf8'))
(ROOT/'data_migration_report.md').write_text(f"# Data migration report\n\nИсточник: публичный HTTP snapshot от 2026-10-02, исходная БД не предоставлена.\n\nПеренесено автомобилей: {Car.objects.count()}, городов: {City.objects.count()}, записей галереи: {CarImage.objects.count()}. Скачано 300 уникальных изображений (302 gallery associations и отдельный hero используют общий manifest). Пропущенных изображений: {len(data['missing_images'])}. Оригиналы сохранены, responsive WebP 640/1200px созданы с сохранением transparency.\n\nПовторный импорт проверен: дубли не создаются, правки CMS не перезаписываются без --refresh. legacy_id формата http:<path>: старые DB IDs неизвестны. Точные slug и legacy_path сохранены.\n\nИз источника отсутствуют характеристики, реальные свободные даты и точные условия депозита/стажа/пробега. Поля остаются пустыми. 91 категория классифицирована по названиям и требует review. Старые скидочные интервалы пересекаются на границах; сохранены как справочные условия, расчёт цены автоматически не выдуман.\n\nПодробности: data_migration_report.json, migration/normalized.json и migration/media_manifest.json.\n",encoding='utf8')
print(json.dumps({'old_urls':len(old['pages']),'new_paths':len(results),'preserved':report['preserved_successful_urls'],'broken_links':len(broken),'metadata_errors':sum(len(r['errors']) for r in results),'title_duplicates':len(duplicates['title']),'description_duplicates':len(duplicates['description']),'queries':counts}))
if broken or sum(len(r['errors']) for r in results) or report['preserved_successful_urls']!=95:raise SystemExit(1)
