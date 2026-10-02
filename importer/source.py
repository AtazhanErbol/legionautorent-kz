"""Live/raw SEO authority layered over preserved extracted catalogue data."""
import copy
import json
import re
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from django.conf import settings

BASE='https://legionautorent.kz'
def read_json(path):return json.loads(Path(path).read_text(encoding='utf8'))
def amount(text):
    match=re.search(r'(\d[\d\s]*)',text)
    return int(re.sub(r'\s','',match[1])) if match else None

def catalogue_source(source=None):
    root=settings.BASE_DIR
    catalogue=copy.deepcopy(read_json(source or root/'migration/normalized.json'))
    old=read_json(root/'seo_audit_old_site.json')
    live_file=root/'migration/rebuild/live_audit.json'
    live=read_json(live_file) if live_file.exists() else {'pages':[]}
    old_map={urlsplit(p['url']).path:p for p in old['pages']}
    live_map={p['path']:p for p in live['pages']}
    improvements=[]
    for kind in ['cities','cars']:
        for item in catalogue[kind]:
            path=item['legacy_path'];page=live_map.get(path)
            folder=root/'migration/rebuild/snapshot'
            if not page or page.get('status')!=200:
                page=old_map.get(path);folder=root/'migration/snapshot'
            if not page or page.get('status')!=200:continue
            soup=BeautifulSoup((folder/page['snapshot_file']).read_text(encoding='utf8'),'html.parser')
            item['slug']=path.removeprefix('/car/') if kind=='cars' else item['slug']
            fallback_title=item['name'] if kind=='cars' else f"Аренда авто без водителя в {item['name_in']} | Legion Auto Rent"
            price_node=soup.select_one('.car_text')
            if kind=='cars':
                price=amount(price_node.get_text(' ',strip=True)) if price_node else None
                if price:item['base_price']=price
                body=soup.select_one('.car_description')
                item['description']=body.decode_contents() if body else ''
                item['active']=True;item['accepts_requests']=True
            else:
                body=soup.select_one('.seo_text')
                item['body']=body.decode_contents() if body else ''
                item['hero_text']='Под режим такси и доставки авто не сдаем!'
            item['seo_title']=page.get('title') or fallback_title
            item['seo_h1']=(page.get('h1') or [item.get('seo_h1') or item['name']])[0]
            description=page.get('description','')
            if not description:
                description=(f"Аренда {item['name']} без водителя от {item['base_price']:,} ₸ в сутки. Фотографии, скидки и условия Legion Auto Rent." if kind=='cars' else f"Прокат автомобилей без водителя в {item['name_in']}. Автопарк Legion Auto Rent, цены от 20 000 ₸, документы и условия аренды.").replace(',',' ')
                improvements.append({'path':path,'field':'description','reason':'Empty legacy meta description filled with factual page-specific copy.'})
            if not page.get('title'):improvements.append({'path':path,'field':'title','reason':'Empty legacy Title filled.'})
            item['seo_description']=description
            item['canonical_url']=page.get('canonical','')
            item['og_title']=page.get('open_graph',{}).get('og:title','')
            item['og_description']=page.get('open_graph',{}).get('og:description','')
            item['og_image']=page.get('open_graph',{}).get('og:image','')
            item['legacy_meta']={'open_graph':page.get('open_graph',{}),'twitter':page.get('twitter',{})}
            item['_raw_seo']=page
    return catalogue,improvements
