"""Read-only HTTP release audit. Production failures cannot silently become passes."""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
from django.conf import settings
import requests


def normalized(value):
    return re.sub(r'\s+', ' ', value or '').strip()


class ReleaseAudit:
    def __init__(self, base_url, mode='production', redirect_origin=None):
        self.base=base_url.rstrip('/')
        self.mode=mode
        self.origin=settings.SITE_URL.rstrip('/')
        self.redirect_origin=redirect_origin
        self.session=requests.Session()
        self.session.headers['User-Agent']='LegionReleaseCheck/1.0 (read-only prelaunch audit)'
        self.failures=[]
        self.warnings=[]
        self.pages={}
        self.sitemap={}
        self.images={}
        self.generated=[]
        self.redirects=[]
        self.checked=0

    def fail(self, path, code, detail=''):
        self.failures.append({'path':path,'check':code,'detail':str(detail)})

    def get(self, path, method='GET', headers=None, direct=False):
        url=path if direct else self.base+path
        try:
            response=self.session.request(method,url,allow_redirects=False,timeout=15,headers=headers)
            self.checked+=1
            return response
        except requests.RequestException as error:
            self.fail(path,'network',str(error).split('?')[0]);return None

    def local_path(self, url):
        parts=urlsplit(url)
        return parts.path+('?' + parts.query if parts.query else '')

    def sitemap_load(self, path='/sitemap.xml', seen=None):
        seen=seen if seen is not None else set()
        if path in seen:
            self.fail(path,'sitemap_cycle');return
        seen.add(path)
        response=self.get(path)
        if response is None:return
        if response.status_code!=200:self.fail(path,'sitemap_status',response.status_code);return
        try:root=ET.fromstring(response.content)
        except ET.ParseError as error:self.fail(path,'sitemap_xml',error);return
        namespace={'s':'http://www.sitemaps.org/schemas/sitemap/0.9','x':'http://www.w3.org/1999/xhtml'}
        if root.tag.endswith('sitemapindex'):
            for loc in root.findall('s:sitemap/s:loc',namespace):
                if not (loc.text or '').startswith(self.origin+'/'):self.fail(path,'sitemap_origin',loc.text)
                self.sitemap_load(self.local_path(loc.text),seen)
        else:
            for entry in root.findall('s:url',namespace):
                url=entry.findtext('s:loc',namespaces=namespace)
                if not url: self.fail(path,'sitemap_empty_url');continue
                if url in self.sitemap:self.fail(url,'sitemap_duplicate')
                if not url.startswith(self.origin+'/'):self.fail(url,'sitemap_origin')
                self.sitemap[url]={n.get('hreflang'):n.get('href') for n in entry.findall('x:link',namespace)}

    def image(self, src):
        url=urljoin(self.origin+'/',src)
        if url in self.images:return
        parsed=urlsplit(url)
        if parsed.scheme=='data':return
        if parsed.scheme!='https':self.fail(src,'mixed_content_image')
        internal=parsed.netloc==urlsplit(self.origin).netloc
        response=self.get(self.local_path(url) if internal else url,method='HEAD',direct=not internal)
        if response is not None and response.status_code==405:
            response=self.get(self.local_path(url) if internal else url,headers={'Range':'bytes=0-0'},direct=not internal)
        self.images[url]=response.status_code if response is not None else None
        if response is not None and response.status_code not in (200,206):self.fail(src,'image_status',response.status_code)

    def page(self,path,expected=200,indexable=True,legacy=None):
        if path in self.pages:return self.pages[path]
        response=self.get(path)
        if response is None:return
        if response.status_code!=expected:self.fail(path,'status',f'{response.status_code}, expected {expected}')
        soup=BeautifulSoup(response.content,'html.parser')
        meta=lambda name,kind='name':(soup.find('meta',attrs={kind:name}) or {}).get('content','')
        canonical=(soup.select_one('link[rel=canonical]') or {}).get('href','')
        heads=soup.select('h1')
        info={'status':response.status_code,'title':soup.title.get_text() if soup.title else '',
              'description':meta('description'),'h1':normalized(heads[0].get_text(' ',strip=True)) if heads else '',
              'canonical':canonical,'robots':meta('robots'),'header_robots':response.headers.get('X-Robots-Tag',''),
              'alternates':{n.get('hreflang'):n.get('href') for n in soup.select('link[rel=alternate][hreflang]')},'indexable':indexable and expected==200}
        self.pages[path]=info
        if response.status_code!=expected:
            return info
        if self.mode!='production':
            if 'noindex' not in info['header_robots'] or 'nofollow' not in info['header_robots']:self.fail(path,'nonproduction_header')
            if 'noindex' not in info['robots'] or 'nofollow' not in info['robots']:self.fail(path,'nonproduction_meta')
        elif indexable and expected==200:
            if 'noindex' in (info['robots']+info['header_robots']):self.fail(path,'production_noindex')
        if expected!=200:return info
        if len(heads)!=1:self.fail(path,'h1_count',len(heads))
        for field in ['title','description','h1']:
            if not info[field]:self.fail(path,field+'_missing')
        expected_canonical=self.origin+urlsplit(path).path
        if canonical!=expected_canonical:self.fail(path,'canonical',f'{canonical} != {expected_canonical}')
        if not canonical.startswith('https://'):self.fail(path,'canonical_https')
        language='kk' if path.startswith('/kk/') else 'en' if path.startswith('/en/') else 'ru'
        if (soup.html or {}).get('lang')!=language:self.fail(path,'html_lang')
        for field in ['og:title','og:description','og:url','og:image']:
            if not meta(field,'property'):self.fail(path,field+'_missing')
        for field in ['twitter:card','twitter:title','twitter:description','twitter:image']:
            if not meta(field):self.fail(path,field+'_missing')
        if meta('og:url','property')!=canonical:self.fail(path,'og_url')
        for image in [meta('og:image','property'),meta('twitter:image')]:
            if image:self.image(image)
        for name in ['Content-Security-Policy','X-Content-Type-Options','X-Frame-Options','Referrer-Policy','Permissions-Policy']:
            if not response.headers.get(name):self.fail(path,'security_header',name)
        if urlsplit(self.base).scheme=='https' and not response.headers.get('Strict-Transport-Security'):self.fail(path,'hsts_missing')
        if response.headers.get('X-Content-Type-Options','').lower()!='nosniff':self.fail(path,'nosniff')
        if "media-src 'self' blob:" not in response.headers.get('Content-Security-Policy',''):self.fail(path,'csp_video_blob')
        for node in soup.select('script[src],link[rel=stylesheet][href],img[src],source[src],video[src],iframe[src]'):
            src=node.get('src') or node.get('href','')
            if src.startswith('http://'):self.fail(path,'mixed_content',src)
        for img in soup.select('img'):
            if not img.get('width') or not img.get('height'):self.fail(path,'image_dimensions',img.get('src'))
            if img.find_parent(class_='car-card') and not img.get('alt'):self.fail(path,'car_alt',img.get('src'))
            if img.get('src'):self.image(img['src'])
            for item in img.get('srcset','').split(','):
                if item.strip():self.image(item.strip().split()[0])
        for source in soup.select('picture source[srcset]'):
            for item in source['srcset'].split(','):
                if item.strip():self.image(item.strip().split()[0])
        schema_nodes=soup.select('script[type="application/ld+json"]')
        if not schema_nodes:self.fail(path,'schema_missing')
        for node in schema_nodes:
            try:
                data=json.loads(node.string or '')
                if not data.get('@type'):self.fail(path,'schema_type')
                if data.get('offers'):
                    price=data['offers'].get('price');visible=soup.select_one('.booking-price')
                    value=re.match(r'[\d\s\u00a0]+',visible.get_text(' ',strip=True)) if visible else None
                    if not value or Decimal(re.sub(r'\s','',value.group()))!=Decimal(price):self.fail(path,'offer_visible_price',price)
            except (ValueError,TypeError,InvalidOperation) as error:self.fail(path,'schema_json',error)
        levels=[int(n.name[1]) for n in soup.select('h1,h2,h3,h4,h5,h6')]
        if any(b>a+1 for a,b in zip(levels,levels[1:])):self.fail(path,'heading_order',levels[:30])
        for field,limit in [('title',60),('description',160)]:
            if len(info[field])>limit:self.warnings.append({'path':path,'check':field+'_length','detail':str(len(info[field]))})
        if legacy:
            for field in ['title','description','h1','canonical']:
                old=legacy.get(field,'')
                if isinstance(old,list):old=' '.join(old)
                if old and normalized(old)!=normalized(info[field]):self.fail(path,'legacy_'+field,old)
                elif not old and field in ('title','description'):self.generated.append({'path':path,'field':field,'value':info[field]})
        return info

    def run(self):
        source=settings.BASE_DIR/'migration/rebuild/live_audit.json'
        records=json.loads(source.read_text(encoding='utf8'))['pages']
        self.sitemap_load()
        for record in records:
            path=record.get('path') or urlsplit(record['url']).path
            good=record['status']==200
            self.page(path,200 if good else 404,good,record if good else None)
            if not good and self.origin+path in self.sitemap:self.fail(path,'legacy_404_in_sitemap')
        for url in list(self.sitemap):self.page(self.local_path(url))
        self.page('/not-a-legion-page-verify/',404,False)
        response=self.get('/styleguide')
        if response is not None:
            if self.mode=='production' and response.status_code!=404:self.fail('/styleguide','production_styleguide',response.status_code)
            if self.mode!='production' and response.status_code==200 and 'noindex' not in response.headers.get('X-Robots-Tag',''):self.fail('/styleguide','styleguide_indexable')
        if any('/styleguide' in url for url in self.sitemap):self.fail('/styleguide','styleguide_sitemap')
        catalog=self.get('/cars/')
        if catalog is not None:
            links={n.get('href') for n in BeautifulSoup(catalog.content,'html.parser').select('.car-card h3 a[href]')}
            expected={urlsplit(p['url']).path for p in records if p['status']==200 and urlsplit(p['url']).path.startswith('/car/')}
            if not expected.issubset(links):self.fail('/cars/','all_91_ssr_links',len(links))
        filtered=self.get('/cars/?sort=price')
        if filtered is not None:
            soup=BeautifulSoup(filtered.content,'html.parser');canonical=(soup.select_one('link[rel=canonical]') or {}).get('href','')
            robots=(soup.find('meta',attrs={'name':'robots'}) or {}).get('content','')
            if 'noindex' not in robots and canonical!=self.origin+'/cars/':self.fail('/cars/?sort=price','indexable_filter')
        for path,info in list(self.pages.items()):
            if info['status']!=200:continue
            if self.origin+path in self.sitemap and self.sitemap[self.origin+path]!=info['alternates']:self.fail(path,'sitemap_html_hreflang_mismatch')
            for lang,url in info['alternates'].items():
                if lang=='x-default':continue
                other=self.page(self.local_path(url))
                if not other:continue
                if self.mode=='production' and 'noindex' in (other['robots']+other['header_robots']):self.fail(path,'hreflang_to_noindex',url)
                if info['canonical'] not in other['alternates'].values():self.fail(path,'hreflang_not_reciprocal',url)
        for language in ['kk','en']:
            response=self.get('/'+language+'/cars/')
            if response is not None:
                soup=BeautifulSoup(response.content,'html.parser')
                robots=(soup.find('meta',attrs={'name':'robots'}) or {}).get('content','')
                if soup.select_one('.translation-notice'):
                    if 'noindex' not in robots:self.fail('/'+language+'/cars/','incomplete_translation_indexable')
                    if self.origin+'/'+language+'/cars/' in self.sitemap:self.fail('/'+language+'/cars/','incomplete_translation_sitemap')
        for field in ['title','description','h1']:
            values=defaultdict(list)
            for path,info in self.pages.items():
                if info['indexable'] and info[field]:values[normalized(info[field]).casefold()].append(path)
            for value,paths in values.items():
                if len(paths)>1:self.fail(', '.join(paths),'duplicate_'+field,value)
        robots=self.get('/robots.txt')
        if robots is not None:
            disallows_all=bool(re.search(r'^Disallow:\s*/\s*$',robots.text,re.M))
            if self.mode=='production' and disallows_all:self.fail('/robots.txt','production_disallow_all')
            if self.mode!='production' and not disallows_all:self.fail('/robots.txt','nonproduction_robots')
            if self.mode=='production' and self.origin+'/sitemap.xml' not in robots.text:self.fail('/robots.txt','sitemap_reference')
        if self.mode=='production':self.check_redirects()
        return self.write_report()

    def check_redirects(self):
        # A loopback HTTP preview cannot prove public DNS/TLS redirects.
        root=urlsplit(self.redirect_origin or self.base)
        if root.hostname in ('127.0.0.1','localhost','testserver'):
            self.fail(self.base,'public_redirects_not_verified','Run with public HTTPS --base-url after deployment; local rendering does not prove DNS/TLS.')
            return
        host=root.netloc.removeprefix('www.')
        for prefix in ['http://'+host,'http://www.'+host,'https://www.'+host]:
            for path in ['/','/kostanay/','/car/lexus-lx-570-superior']:
                response=self.get(prefix+path,method='HEAD',direct=True)
                if response is None:continue
                expected='https://'+host+path
                row={'url':prefix+path,'status':response.status_code,'location':response.headers.get('Location',''),'expected':expected};self.redirects.append(row)
                if response.status_code not in (301,308) or row['location']!=expected:self.fail(prefix+path,'redirect_one_hop',row)
                else:
                    final=self.get(expected,method='HEAD',direct=True)
                    if final is not None and final.status_code!=200:self.fail(expected,'redirect_target',final.status_code)

    def write_report(self):
        report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'base_url':self.base,'mode':self.mode,'passed':not self.failures,'requests':self.checked,
                'pages':len(self.pages),'sitemap_urls':len(self.sitemap),'unique_images':len(self.images),'failures':self.failures,'warnings':self.warnings,'generated_legacy_metadata':self.generated,'redirects':self.redirects}
        folder=settings.BASE_DIR/'reports';folder.mkdir(exist_ok=True)
        (folder/'prelaunch_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        lines=['# Prelaunch report','',f"UTC: {report['timestamp_utc']}",f'Base URL: {self.base}',f'Mode: {self.mode}',f"Result: {'PASS' if report['passed'] else 'FAIL'}",'',f'{len(self.pages)} pages; {len(self.sitemap)} sitemap URLs; {len(self.images)} unique image resources; {self.checked} HTTP requests.','',
               'Meaningful legacy SEO values are protected. Duplicates are reported as failures and are never rewritten by this checker. Length recommendations are warnings. Empty old metadata filled in the existing rebuild is listed separately.','', '## Failures','']
        lines += [f"- `{x['check']}` — `{x['path']}`: {x['detail']}" for x in self.failures] or ['None.']
        lines += ['', '## Warnings','']+[f"- `{x['check']}` — `{x['path']}`: {x['detail']}" for x in self.warnings]
        lines += ['', '## Generated values where the snapshot was empty','']+[f"- `{x['path']}` / {x['field']}: {x['value']}" for x in self.generated]
        lines += ['', '## Redirect evidence','']+[f"- `{x['url']}` → {x['status']} `{x['location']}`" for x in self.redirects]
        lines += ['', 'This audit never submits leads, changes data, generates media or deploys the site. A local audit is not a production launch approval.','']
        (folder/'prelaunch_report.md').write_text('\n'.join(lines),encoding='utf8')
        return report
