"""Read-only, bounded crawl of the public legacy site. Never submits forms."""
import argparse
import csv
import hashlib
import json
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup, Comment

BASE = 'https://legionautorent.kz'
ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'migration' / 'snapshot'


def clean(node):
    return node.get_text(' ', strip=True) if node else ''


def metadata(html, url, status, final_url):
    soup = BeautifulSoup(html, 'html.parser')
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    meta = {m.get('name', m.get('property', '')): m.get('content', '') for m in soup.select('meta')}
    canonical = soup.select_one('link[rel="canonical"]')
    images = []
    for img in soup.select('img'):
        src = img.get('src', img.get('data-src', ''))
        if src:
            images.append({'src': urljoin(url, src), 'alt': img.get('alt', ''), 'width': img.get('width'), 'height': img.get('height')})
    for node in soup.select('[style]'):
        for src in re.findall(r"url\(['\"]?([^)'\"]+)", node['style']):
            images.append({'src': urljoin(url, src), 'alt': '', 'background': True})
    links = sorted({urljoin(url, a['href']).split('#')[0] for a in soup.select('a[href]') if a['href'] and not a['href'].startswith(('tel:', 'mailto:', 'javascript:'))})
    schemas = []
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            schemas.append(json.loads(s.string or s.get_text()))
        except ValueError:
            schemas.append({'parse_error': True, 'raw': s.get_text()})
    forms = [{'action': f.get('action', ''), 'method': f.get('method', 'GET'), 'fields': [x.get('name', '') for x in f.select('input, select, textarea')]} for f in soup.select('form')]
    scripts = '\n'.join(s.get_text() for s in soup.select('script') if s.get('type') != 'application/ld+json')
    scripts += '\n' + '\n'.join(s.get('src', '') for s in soup.select('script[src]'))
    analytics = {'gtm': sorted(set(re.findall(r'GTM-[A-Z0-9]+', scripts))), 'ga4': sorted(set(re.findall(r'G-[A-Z0-9]+', scripts))), 'metrika': sorted(set(re.findall(r'ym\(\s*(\d+)', scripts))), 'ads': sorted(set(re.findall(r'AW-\d+', scripts)))}
    headings = {f'h{i}': [clean(x) for x in soup.select(f'h{i}')] for i in (1, 2, 3)}
    for node in soup.select('script, style, noscript, header, footer, nav'):
        node.decompose()
    main = soup.select_one('main') or soup.body or soup
    errors = []
    title = clean(soup.title)
    if not title: errors.append('missing_title')
    if not meta.get('description'): errors.append('missing_description')
    h1 = headings['h1']
    if len(h1) != 1: errors.append(f'h1_count_{len(h1)}')
    if not canonical: errors.append('missing_canonical')
    if any(not x['alt'] for x in images): errors.append('missing_alt')
    if 'Заполните текст в админке' in clean(main): errors.append('placeholder_content')
    return {'url': url, 'status': status, 'final_url': final_url, 'title': title, 'description': meta.get('description', ''), **headings, 'canonical': urljoin(url, canonical.get('href', '')) if canonical else '', 'robots': meta.get('robots', 'index,follow'), 'open_graph': {k: v for k, v in meta.items() if k.startswith('og:')}, 'twitter': {k: v for k, v in meta.items() if k.startswith('twitter:')}, 'schemas': schemas, 'breadcrumb': [clean(x) for x in soup.select('[class*=breadcrumb]')], 'text': clean(main), 'links': links, 'images': images, 'slug': urlsplit(url).path.rstrip('/').split('/')[-1], 'indexable': status == 200 and 'noindex' not in meta.get('robots', ''), 'forms': forms, 'analytics': analytics, 'errors': errors}


def run(max_pages=400):
    AUDIT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers['User-Agent'] = 'LegionMigrationAudit/1.0 (read-only owner-requested migration)'
    report = {'captured_at': datetime.now(timezone.utc).isoformat(), 'base': BASE, 'resources': {}, 'pages': [], 'errors': []}
    queue = deque([BASE + '/'])
    for path in ['/robots.txt', '/sitemap.xml']:
        try:
            resp = session.get(BASE + path, timeout=30)
            (AUDIT / path.lstrip('/')).write_text(resp.text, encoding='utf-8')
            report['resources'][path] = {'status': resp.status_code, 'headers': dict(resp.headers), 'url': resp.url}
            if path.endswith('.xml') and resp.ok:
                tree = ElementTree.fromstring(resp.content)
                for node in tree.iter():
                    if node.tag.endswith('loc') and urlsplit(node.text or '').hostname == urlsplit(BASE).hostname:
                        queue.append(node.text)
        except Exception as exc:
            report['errors'].append({'url': BASE + path, 'error': str(exc)})
    seen = set()
    while queue and len(seen) < max_pages:
        url = queue.popleft().split('#')[0]
        parsed = urlsplit(url)
        if url in seen or parsed.query or parsed.hostname != urlsplit(BASE).hostname:
            continue
        if re.search(r'\.(jpg|jpeg|png|webp|gif|svg|css|js|pdf|ico)$', parsed.path, re.I): continue
        if parsed.path.startswith(('/admin', '/ajax', '/api')): continue
        seen.add(url)
        try:
            response = session.get(url, timeout=30)
            if 'html' not in response.headers.get('Content-Type', ''): continue
            name = hashlib.sha256(url.encode()).hexdigest()[:20] + '.html'
            (AUDIT / name).write_text(response.text, encoding='utf-8')
            item = metadata(response.text, url, response.status_code, response.url)
            item.update({'snapshot_file': name, 'headers': dict(response.headers), 'redirects': [{'url': h.url, 'status': h.status_code, 'location': h.headers.get('Location')} for h in response.history]})
            report['pages'].append(item)
            print(f"{len(report['pages']):03} {response.status_code} {parsed.path}", flush=True)
            if response.ok: queue.extend(item['links'])
        except requests.RequestException as exc:
            report['errors'].append({'url': url, 'error': str(exc)})
            print(f'ERROR {url}: {exc}', flush=True)
        time.sleep(0.08)
    report['complete_queue'] = not queue
    report['unvisited'] = list(queue)
    out = ROOT / 'seo_audit_old_site.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    fields = ['url', 'status', 'title', 'description', 'h1', 'h2', 'h3', 'canonical', 'robots', 'indexable', 'slug', 'errors', 'images', 'links', 'open_graph', 'twitter', 'schemas', 'breadcrumb', 'text']
    with (ROOT / 'seo_audit_old_site.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for item in report['pages']:
            w.writerow({k: json.dumps(item[k], ensure_ascii=False) if isinstance(item[k], (list, dict)) else item[k] for k in fields})
    print(json.dumps({'pages': len(report['pages']), 'errors': len(report['errors']), 'complete': report['complete_queue']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-pages', type=int, default=400)
    run(parser.parse_args().max_pages)
