"""Compare all legacy routes against rendered SSR HTML, without touching catalogue data."""
import csv,json,re
from pathlib import Path
from urllib.parse import urlsplit
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.test import Client,override_settings
from bs4 import BeautifulSoup
from importer.source import catalogue_source
from seo.services import languages_for
from core.i18n import language_url
from cars.models import Car
from locations.models import City

def plain(value):return re.sub(r'\s+',' ',value or '').strip()
class Command(BaseCommand):
    help='Check every preserved URL, SEO fields, hreflang, content, gallery and JSON-LD; write CSV reports.'
    def handle(self,*args,**options):
        root=settings.BASE_DIR;reports=root/'reports';reports.mkdir(exist_ok=True)
        old=json.loads((root/'seo_audit_old_site.json').read_text(encoding='utf8'))
        live=json.loads((root/'migration/rebuild/live_audit.json').read_text(encoding='utf8'))
        current={p['path']:p for p in live['pages']}
        source,_=catalogue_source();objects={p['legacy_path']:p for key in ['cities','cars'] for p in source[key]}
        audit=[];comparison=[];failures=[];client=Client()
        with override_settings(IS_STAGING=False,SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver','localhost','127.0.0.1']):
            for record in old['pages']:
                path=urlsplit(record['url']).path;raw=current.get(path,record)
                audit.append({'url':record['url'],'original_status':record['status'],'live_status':raw['status'],'title':raw['title'],'description':raw['description'],'h1':' | '.join(raw.get('h1',[])),'canonical':raw['canonical'],'word_count':len(raw.get('text','').split()),'images':len(raw.get('images',[])),'internal_links':len(raw.get('links',[])),'live_checked_at':live['captured_at']})
                response=client.get(path);soup=BeautifulSoup(response.content,'html.parser')
                title=soup.title.get_text() if soup.title else '';desc=soup.find('meta',attrs={'name':'description'});desc=desc.get('content','') if desc else ''
                headings=soup.select('h1');h1=headings[0].get_text(' ',strip=True) if headings else ''
                canonical=soup.select_one('link[rel=canonical]');canonical=canonical.get('href','') if canonical else ''
                source_obj=objects.get(path);issues=[];expected_status=200 if raw['status']==200 else 404
                if response.status_code!=expected_status:issues.append('status')
                new_gallery=len(soup.select('.gallery-track figure'))
                old_gallery=raw.get('gallery_count',0)
                schema_count=0
                if expected_status==200 and source_obj:
                    for field,new_value in [('title',title),('description',desc),('h1',h1)]:
                        expected=source_obj[{'title':'seo_title','description':'seo_description','h1':'seo_h1'}[field]]
                        if plain(new_value)!=plain(expected):issues.append(field)
                    if len(headings)!=1:issues.append('h1_count')
                    if canonical!=(raw['canonical'] or settings.SITE_URL+path):issues.append('canonical')
                    alternates={n.get('hreflang'):n.get('href') for n in soup.select('link[rel=alternate][hreflang]')}
                    obj=(Car.objects if path.startswith('/car/') else City.objects).prefetch_related('translations').get(legacy_path=path)
                    expected_alternates={lang:settings.SITE_URL+language_url(path,lang) for lang in languages_for(obj)}
                    expected_alternates['x-default']=settings.SITE_URL+path
                    if alternates!=expected_alternates:issues.append('hreflang_published_complete')
                    for property,value in raw.get('open_graph',{}).items():
                        if property=='og:url' and isinstance(obj,City):value=canonical
                        node=soup.find('meta',attrs={'property':property})
                        if value and (not node or node.get('content')!=value):issues.append(property)
                    body=source_obj.get('body') or source_obj.get('description')
                    if body:
                        source_text=plain(BeautifulSoup(body,'html.parser').get_text(' ',strip=True))
                        if source_text not in plain(soup.get_text(' ',strip=True)):issues.append('seo_text')
                    if path.startswith('/car/') and new_gallery!=old_gallery:issues.append('gallery_count')
                    if path in ['/','/kostanay/','/ustkamenogorsk/','/pavlodar/']:
                        old_soup=BeautifulSoup((root/'migration/rebuild/snapshot'/raw['snapshot_file']).read_text(encoding='utf8'),'html.parser')
                        old_cars={urlsplit(n['href']).path for n in old_soup.select('a[href]') if urlsplit(n['href']).path.startswith('/car/')}
                        new_cars={urlsplit(n['href']).path for n in soup.select('.car-card a[href]') if urlsplit(n['href']).path.startswith('/car/')}
                        if old_cars!=new_cars:issues.append('city_car_links')
                    try:
                        for node in soup.select('script[type="application/ld+json"]'):
                            schema=json.loads(node.string);assert schema.get('@context') and schema.get('@type');schema_count+=1
                        if schema_count<3:issues.append('schemas_missing')
                    except (ValueError,AssertionError):issues.append('schema_json')
                passed=not issues
                row={'url':record['url'],'original_status':record['status'],'live_status':raw['status'],'new_status':response.status_code,'expected_status':expected_status,'old_title':raw['title'],'new_title':title,'old_description':raw['description'],'new_description':desc,'old_h1':' | '.join(raw.get('h1',[])),'new_h1':h1,'old_canonical':raw['canonical'],'new_canonical':canonical,'old_images':len(raw.get('images',[])),'new_images':len(soup.select('img')),'old_gallery_images':old_gallery,'new_gallery_images':new_gallery,'schema_count':schema_count,'pass':passed,'issues':';'.join(issues),'note':'Recovery pending: old 500 returns honest 404' if expected_status==404 else 'Empty legacy SEO filled' if not raw['title'] or not raw['description'] else ''}
                comparison.append(row)
                if not passed:failures.append({'path':path,'issues':issues})
        for name,rows in [('old_site_audit.csv',audit),('url_comparison.csv',comparison)]:
            with (reports/name).open('w',newline='',encoding='utf-8-sig') as f:writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        result={'legacy_urls':len(comparison),'preserved_200':sum(r['new_status']==200 for r in comparison),'old_500_now_404':sum(r['live_status']==500 and r['new_status']==404 for r in comparison),'passed':sum(r['pass'] for r in comparison),'failures':failures}
        (reports/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');self.stdout.write(json.dumps(result,ensure_ascii=False))
        if failures:raise CommandError('Migration verification failed; inspect reports/url_comparison.csv')
