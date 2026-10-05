"""Check the rendered brand spelling and favicon without changing content."""
import os
import sys
import json
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','legion.settings')
import django
django.setup()
from django.apps import apps
from django.test import Client
from bs4 import BeautifulSoup
from core.branding import BRAND, _OLD_BRAND

paths={'/','/cars/','/faq/','/booking/','/callback/','/control-legion/login/'}
for label,field in [('cars.Car','legacy_path'),('locations.City','legacy_path'),('pages.Page','path')]:
    paths.update(apps.get_model(label).objects.filter(active=True).values_list(field,flat=True))
paths.update('/'+lang+path for lang in ('kk','en') for path in ('/','/contacts/','/privacy/','/cars/','/booking/'))
client=Client();errors=[];favicons=set()
for path in sorted(paths):
    response=client.get(path);soup=BeautifulSoup(response.content,'html.parser')
    for node in soup.select('script,style'):node.decompose()
    text=soup.get_text(' ',strip=True)+' '+' '.join(n.get('content','') for n in soup.select('meta[content]'))+' '+' '.join(n.get('alt','') for n in soup.select('img'))
    wrong=[m.group(0) for m in _OLD_BRAND.finditer(text) if m.group(0)!=BRAND]
    if wrong or response.status_code!=200:errors.append({'path':path,'status':response.status_code,'old_names':wrong})
    icon=soup.select_one('link[rel=icon]')
    if not icon:errors.append({'path':path,'missing_favicon':True})
    else:favicons.add(icon['href'])
report={'brand':BRAND,'pages':len(paths),'errors':errors,'favicons':sorted(favicons),'favicon_sha256':hashlib.sha256((ROOT/'static/img/favicon-original.jpg').read_bytes()).hexdigest()}
(ROOT/'reports/brand_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
if errors:raise SystemExit(1)
