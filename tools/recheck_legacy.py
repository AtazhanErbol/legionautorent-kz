"""Owner-requested read-only live verification; preserves every original snapshot."""
import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree
import requests
from bs4 import BeautifulSoup
from crawl_legacy import metadata

ROOT=Path(__file__).resolve().parents[1]
BASE='https://legionautorent.kz'
OUT=ROOT/'migration/rebuild';OUT.mkdir(parents=True,exist_ok=True)
SNAP=OUT/'snapshot';SNAP.mkdir(exist_ok=True)
REPORTS=ROOT/'reports';REPORTS.mkdir(exist_ok=True)
AGENT='LegionRebuildVerification/2.0 (owner-requested read-only audit)'
session=requests.Session();session.headers['User-Agent']=AGENT
def fetch(path):
    time.sleep(.3)
    return session.get(urljoin(BASE,path),timeout=(10,35))

old=json.loads((ROOT/'seo_audit_old_site.json').read_text(encoding='utf8'))
robots_response=fetch('/robots.txt');(SNAP/'robots.txt').write_text(robots_response.text,encoding='utf8')
robots=RobotFileParser();robots.parse(robots_response.text.splitlines())
sitemap_urls=set();queue=['/sitemap.xml'];seen=set()
while queue and len(seen)<20:
    url=queue.pop(0)
    if url in seen:continue
    seen.add(url);response=fetch(url)
    (SNAP/('sitemap-'+hashlib.sha256(url.encode()).hexdigest()[:8]+'.xml')).write_text(response.text,encoding='utf8')
    if not response.ok:continue
    try:tree=ElementTree.fromstring(response.content)
    except ElementTree.ParseError:continue
    for node in tree.iter():
        if node.tag.endswith('loc') and node.text and urlsplit(node.text).hostname=='legionautorent.kz':
            if tree.tag.endswith('sitemapindex'):queue.append(node.text)
            else:sitemap_urls.add(node.text)

paths=list(dict.fromkeys([urlsplit(p['url']).path for p in old['pages']]+[urlsplit(u).path for u in sorted(sitemap_urls)]))
report={'captured_at':datetime.now(timezone.utc).isoformat(),'pages':[],'sitemap_urls':sorted(sitemap_urls),'errors':[]}
def inspect(path):
    if not robots.can_fetch(AGENT,BASE+path):return {'path':path,'status':None,'blocked_by_robots':True}
    try:
        response=fetch(path);name=hashlib.sha256(path.encode()).hexdigest()[:20]+'.html'
        (SNAP/name).write_text(response.text,encoding='utf8')
        item=metadata(response.text,BASE+path,response.status_code,response.url)
        soup=BeautifulSoup(response.text,'html.parser')
        item.update(path=path,snapshot_file=name,lang=(soup.html.get('lang','') if soup.html else ''),in_sitemap=BASE+path in sitemap_urls,
                    kazakh_letter_count=len(re.findall('[әғқңөұүһіӘҒҚҢӨҰҮҺІ]',item['text'])),
                    headers=dict(response.headers),redirects=[{'url':r.url,'status':r.status_code,'location':r.headers.get('Location')} for r in response.history])
        item['gallery_count']=len(soup.select('.car_inner_img'))
        return item
    except requests.RequestException as error:return {'path':path,'status':None,'error':type(error).__name__}

for i,path in enumerate(paths):
    item=inspect(path);report['pages'].append(item)
    print(f"RU {i+1}/{len(paths)} {item['status']} {path}",flush=True)
    if i%10==0:(OUT/'live_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

# Inspect every existing RU equivalent and any /kz/ URLs discovered in sitemap/links.
kz_paths=set('/kz'+p for p in paths if not p.startswith(('/kz','/kk','/en')))
for item in report['pages']:
    kz_paths.update(urlsplit(u).path for u in item.get('links',[]) if urlsplit(u).hostname=='legionautorent.kz' and urlsplit(u).path.startswith('/kz/'))
kz=[]
for i,path in enumerate(sorted(kz_paths)):
    item=inspect(path);kz.append(item)
    print(f"KZ {i+1}/{len(kz_paths)} {item['status']} {path}",flush=True)
    if i%10==0:(OUT/'kazakh_audit.json').write_text(json.dumps(kz,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'live_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'kazakh_audit.json').write_text(json.dumps(kz,ensure_ascii=False,indent=2),encoding='utf8')
live_by_path={p['path']:p for p in report['pages']}
old_sitemap=(ROOT/'migration/snapshot/sitemap.xml').read_text(encoding='utf8')
failed=[]
for page in old['pages']:
    if page['status']!=500:continue
    path=urlsplit(page['url']).path;live=live_by_path.get(path,{})
    linked=[p['url'] for p in old['pages'] if page['url'] in p.get('links',[])]
    current_links=[p['url'] for p in report['pages'] if page['url'] in p.get('links',[])]
    # An unavailable distinct vehicle cannot be safely replaced by a similar model.
    recommendation='fix_from_owner_database_and_serve_200' if page['url'] in old_sitemap or linked else '404_unless_valid_content_is_recovered'
    failed.append({'url':page['url'],'old_status':500,'live_status':live.get('status'),'still_500':live.get('status')==500,'old_sitemap':page['url'] in old_sitemap,'live_sitemap':page['url'] in sitemap_urls,'old_internal_links':len(linked),'live_internal_links':len(current_links),'recommendation':recommendation,'temporary_new_status':200 if live.get('status')==200 else 404,'notes':'No automatic redirect: distinct vehicle; recovery preferred. A specific 301 requires evidence of the same replacement vehicle.'})
with (REPORTS/'legacy_500_recheck.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=list(failed[0]));writer.writeheader();writer.writerows(failed)
with (REPORTS/'kazakh_url_audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['path','status','lang','kazakh_letter_count','in_sitemap','canonical','robots','redirects']
    writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(kz)

# Save first-party palette/branding evidence; design reference images are not shipped.
brand=OUT/'brand';brand.mkdir(exist_ok=True)
for path,name in [('/css/style.css?v=1.30','legacy.css'),('/img/legionautorent.svg','legionautorent.svg')]:
    response=fetch(path);response.raise_for_status();(brand/name).write_bytes(response.content)
colors=Counter(re.findall(r'#[0-9a-fA-F]{3,8}\b',(brand/'legacy.css').read_text(encoding='utf8',errors='replace')))
(brand/'palette.json').write_text(json.dumps({'css_colors':colors.most_common(),'logo_colors':sorted(set(re.findall(r'#[0-9a-fA-F]{3,8}\b',(brand/'legionautorent.svg').read_text(encoding='utf8'))))},indent=2),encoding='utf8')
print(json.dumps({'ru_statuses':dict(Counter(p.get('status') for p in report['pages'])),'kz_statuses':dict(Counter(p.get('status') for p in kz)),'real_kazakh':sum(p.get('status')==200 and p.get('kazakh_letter_count',0)>10 for p in kz),'failed_rechecked':len(failed),'palette':colors.most_common(8)}))
