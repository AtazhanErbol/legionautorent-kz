import csv
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup
from crawl_legacy import metadata

ROOT = Path(__file__).resolve().parents[1]
CITY = {'/': ('Астана', 'Астане', 'astana'), '/kostanay/': ('Костанай', 'Костанае', 'kostanay'), '/ustkamenogorsk/': ('Усть-Каменогорск', 'Усть-Каменогорске', 'ustkamenogorsk'), '/pavlodar/': ('Павлодар', 'Павлодаре', 'pavlodar')}

def number(text):
    match = re.search(r'(\d[\d\s]*)', text)
    return int(re.sub(r'\s', '', match[1])) if match else None

def category(name):
    n = name.lower()
    if any(t in n for t in ['s-63', 's-500', 's 400', 's221', 's-550', '530i']): return 'premium'
    if any(t in n for t in ['cruiser', 'lc 200', 'lx 570', 'tahoe', 'x6', 'g 500', 'range rover', 'tucson', 'sportage', 'spotage', 'santa fe', 'highlander', 'rav4', 'seltos', 'creta', 'tiggo', 'x5', 'l7', 'mufasa']): return 'suv'
    if any(t in n for t in ['camry xv 70', 'camry xv70', 'camry xv 75', 'camry xv 80', 'sonata', 'k-5', 'gs 350', 'es 250', 'e class']): return 'business'
    if any(t in n for t in ['cobalt', 'accent']): return 'economy'
    return 'comfort'

def normalize():
    audit = json.loads((ROOT / 'seo_audit_old_site.json').read_text(encoding='utf8'))
    normalized = {'source': 'public-http-snapshot', 'captured_at': audit['captured_at'], 'cities': [], 'cars': [], 'content_changes': [], 'image_errors': []}
    membership = {}
    for p in audit['pages']:
        s = BeautifulSoup((ROOT / 'migration/snapshot' / p['snapshot_file']).read_text(encoding='utf8'), 'html.parser')
        refreshed = metadata(str(s), p['url'], p['status'], p['final_url'])
        p.update(refreshed)
        path = urlsplit(p['url']).path
        if p['status'] != 200 or path not in CITY: continue
        name, name_in, slug = CITY[path]
        block = s.select_one('.seo_text')
        body = block.decode_contents() if block else ''
        if path in ('/kostanay/', '/ustkamenogorsk/'):
            body = body.replace('в Астане', 'в ' + name_in)
            normalized['content_changes'].append({'path': path, 'reason': 'Corrected incorrect Astana reference and added city-specific fleet information.'})
        if 'Заполните текст в админке' in body:
            body = f'<h3>Прокат автомобилей в {name_in}</h3><p>В каталоге Legion Auto Rent для Павлодара представлены автомобили разных классов. Выберите модель и оставьте заявку: менеджер уточнит даты аренды, место получения и условия.</p>'
            normalized['content_changes'].append({'path': path, 'reason': 'Removed public CMS placeholder; factual city-specific replacement, address remains unset.'})
        if path == '/kostanay/': body += '<p>В Костанае офис Legion Auto Rent расположен на улице Дощанова, 157, офис 1. В городском автопарке представлены Hyundai, Toyota, Kia и Chery; тарифы указаны на странице каждого автомобиля.</p>'
        if path == '/ustkamenogorsk/': body += '<p>В Усть-Каменогорске офис находится на улице Пограничной, 58/2, офис 9. В каталоге города можно выбрать седан или внедорожник; получение и возврат согласовываются с менеджером.</p>'
        address = s.select_one('footer .loc')
        address = address.get_text(' ', strip=True) if address else ''
        if 'укажите' in address: address = ''
        map_node = s.select_one('footer iframe')
        normalized['cities'].append({'name': name, 'name_in': name_in, 'slug': slug, 'legacy_path': path, 'seo_title': p['title'] or f'Аренда авто без водителя в {name_in} | Legion Auto Rent', 'seo_description': p['description'] or f'Прокат автомобилей без водителя в {name_in}. Актуальный автопарк, цены в тенге, скидки при длительной аренде. Оставьте заявку в Legion Auto Rent.', 'seo_h1': p['h1'][0] if p['h1'] else f'Прокат авто без водителя в {name_in}', 'body': body, 'address': address, 'phone': '+7 (705) 727-77-77', 'map_url': map_node.get('src', '').strip() if map_node else '', 'sort_order': len(normalized['cities']), 'og_title': p['open_graph'].get('og:title', ''), 'og_description': p['open_graph'].get('og:description', '')})
        for link in s.select('.car_item a[href^="/car/"]'):
            membership.setdefault(link['href'], []).append(slug)
    for p in audit['pages']:
        path = urlsplit(p['url']).path
        if p['status'] != 200 or not path.startswith('/car/'): continue
        s = BeautifulSoup((ROOT / 'migration/snapshot' / p['snapshot_file']).read_text(encoding='utf8'), 'html.parser')
        h1 = s.select_one('h1')
        name = h1.get_text(' ', strip=True).removeprefix('Аренда ') if h1 else p['title']
        price = number(s.select_one('.car_price').get_text(' ', strip=True)) if s.select_one('.car_price') else None
        if not price: raise ValueError(f'Missing price: {path}')
        first = name.split()[0].lower()
        brands = {'bmw': 'BMW', 'mercedes': 'Mercedes-Benz', 'mercedes-benz': 'Mercedes-Benz', 'range': 'Land Rover', 'lixiang': 'Li Auto', 'kia': 'Kia', 'jac': 'JAC'}
        brand = brands.get(first, first.title())
        gallery = []
        for item in s.select('.car_inner_img'):
            img = item.select_one('img')
            src = item.get('data-src', '') or (img.get('src', '') if img else '')
            if src:
                gallery.append({'url': urljoin(p['url'], src), 'alt': (img.get('alt') if img else '') or name, 'sort_order': len(gallery)})
        discounts = []
        for item in s.select('.term_item'):
            label = item.select_one('.term_duration').get_text(' ', strip=True)
            nums = re.findall(r'\d+', label)
            discounts.append({'label': label, 'min_days': int(nums[0]), 'max_days': int(nums[1]) if len(nums) > 1 else None, 'percent': number(item.select_one('.term_discount').get_text(' ', strip=True))})
        normalized['cars'].append({'name': name, 'slug': path.split('/')[-1], 'legacy_path': path, 'legacy_id': 'http:' + path, 'brand': brand, 'model_name': name.split(' ', 1)[-1], 'category': category(name), 'category_inferred': True, 'cities': list(dict.fromkeys(membership.get(path, []))), 'base_price': price, 'seo_title': p['title'] or name + ' | Legion Auto Rent', 'seo_description': p['description'] or f'Аренда {name} без водителя: {price:,} ₸ в сутки. Фотографии, скидки при длительной аренде и заявка менеджеру в Legion Auto Rent.'.replace(',', ' '), 'seo_h1': p['h1'][0] if p['h1'] else 'Аренда ' + name, 'og_title': p['open_graph'].get('og:title', ''), 'og_description': p['open_graph'].get('og:description', ''), 'images': gallery, 'discounts': discounts, 'featured': path in ['/car/toyota-camry-xv-70-prestige-plus', '/car/hyundai-sonata-n-line', '/car/chevrolet-cobalt', '/car/kia-sportage', '/car/toyota-camry-xv-80', '/car/mercedes-s-500'], 'sort_order': len(normalized['cars'])})
    (ROOT / 'migration/normalized.json').write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding='utf8')
    (ROOT / 'seo_audit_old_site.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf8')
    with (ROOT / 'seo_audit_old_site.csv').open('w', newline='', encoding='utf-8-sig') as f:
        fields = list(audit['pages'][0].keys())
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader()
        for p in audit['pages']: w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in p.items()})
    with (ROOT / 'seo_url_migration.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['OLD_URL', 'NEW_URL', 'OLD_STATUS', 'NEW_STATUS', 'REDIRECT', 'NOTES'])
        for p in audit['pages']:
            w.writerow([p['url'], p['url'], p['status'], '200' if p['status'] == 200 else '404', 'NONE', 'Exact URL retained' if p['status'] == 200 else 'Legacy 500: content unavailable, restore from DB or confirm specific redirect before release'])
    print(json.dumps({'cities': len(normalized['cities']), 'cars': len(normalized['cars']), 'images': sum(len(c['images']) for c in normalized['cars']), 'orphan_cars': [c['legacy_path'] for c in normalized['cars'] if not c['cities']]}, ensure_ascii=True))

if __name__ == '__main__': normalize()
