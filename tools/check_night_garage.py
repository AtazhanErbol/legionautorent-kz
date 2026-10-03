"""Read-only headed Chrome review of the approved design across page types."""
import argparse
import json
import os
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legion.settings')
import django
django.setup()
from django.test import RequestFactory
from django.utils.translation import override
from core.views import server_error

parser = argparse.ArgumentParser()
parser.add_argument('--round', default='1')
parser.add_argument('--headless', action='store_true')
args = parser.parse_args()
OUT = ROOT / 'output/playwright' / f'night-garage-round{args.round}'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'http://127.0.0.1:8002'
report = {'round': args.round, 'headed_chrome': not args.headless, 'layouts': [], 'checks': {}, 'errors': [], 'failures': []}
routes = [('home','/'), ('city','/kostanay/'), ('city-east','/ustkamenogorsk/'), ('city-pavlodar','/pavlodar/'), ('catalog','/cars/'), ('car','/car/lexus-lx-570-superior'),
          ('conditions','/rental-conditions/'), ('faq','/faq/'), ('contacts','/contacts/'), ('404','/review-missing-page/')]
widths = [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844),(320,740)]
def check(name, value, detail=None):
    report['checks'][name] = bool(value)
    if not value: report['failures'].append({'check': name, 'detail': detail})
def shot(page, name, full=False):
    page.screenshot(path=str(OUT / (name+'.png')), full_page=full)
def inspect(page, language, name, width, status):
    row = page.evaluate('''()=>{
      const h=document.querySelector('h1'),header=document.querySelector('.header-inner')||document.querySelector('header');
      const nodes=[...header.children].filter(n=>{const r=n.getBoundingClientRect();return r.width&&r.height});
      const overlap=[];for(let i=1;i<nodes.length;i++)if(nodes[i-1].getBoundingClientRect().right>nodes[i].getBoundingClientRect().left+1)overlap.push(nodes[i].className);
      return {overflow:document.documentElement.scrollWidth>innerWidth,headerOverlap:overlap,h1:document.querySelectorAll('h1').length,h1Lines:Math.round(h.getBoundingClientRect().height/parseFloat(getComputedStyle(h).lineHeight)),font:getComputedStyle(h).fontFamily,lang:document.documentElement.lang,
        clipped:[...document.querySelectorAll('h1,.button,.hero-facts strong')].filter(n=>n.offsetWidth&&n.scrollWidth>n.clientWidth+2).map(n=>n.textContent.trim())};
    }''')
    row.update(language=language,page=name,width=width,status=status)
    report['layouts'].append(row)
    (OUT/'progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    check(f'{language}_{name}_{width}',status==(404 if name=='404' else 500 if name=='500' else 200) and not row['overflow'] and not row['headerOverlap'] and row['h1']==1 and not row['clipped'] and row['lang']==language and (not name.startswith('city') or row['h1Lines']<=3),row)

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=args.headless)
    for language in ['ru','kk','en']:
        context=browser.new_context()
        page=context.new_page()
        page.on('pageerror',lambda error:report['errors'].append(str(error)))
        prefix='' if language=='ru' else '/'+language
        for width,height in widths:
            page.set_viewport_size({'width':width,'height':height})
            for name,path in routes:
                response=page.goto(BASE+prefix+path,wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                page.wait_for_timeout(100)
                inspect(page,language,name,width,response.status)
                if width in (1440,390):
                    shot(page,f'{language}-{name}-{width}')
                    if language=='ru':
                        for section in page.locator('main section').all():
                            section.scroll_into_view_if_needed();page.wait_for_timeout(160)
                        page.evaluate('scrollTo({top:0,behavior:"instant"})');page.wait_for_timeout(250)
                        style=page.add_style_tag(content='.car-card{content-visibility:visible!important}')
                        shot(page,f'{language}-{name}-{width}-full',True)
                        style.evaluate('n=>n.remove()')
                        if name=='home':
                            card=page.locator('.car-card').first;card.scroll_into_view_if_needed();page.wait_for_timeout(500)
                            card.screenshot(path=str(OUT/f'card-{width}.png'))
        for name,path in [('booking','/booking/'),('callback','/callback/'),('privacy','/privacy/'),('consent','/consent/'),('success','/request-success/')]:
            for width,height in [(1440,900),(390,844),(320,740)]:
                page.set_viewport_size({'width':width,'height':height})
                response=page.goto(BASE+prefix+path,wait_until='networkidle');page.evaluate('document.fonts.ready')
                inspect(page,language,name,width,response.status)
                if width in (1440,390):shot(page,f'{language}-{name}-{width}')
        # Render the actual database-independent handler in a browser-only route.
        with override(language):
            request=RequestFactory().get('/');request.LANGUAGE_CODE=language
            error=server_error(request)
        error_path=BASE+prefix+'/review-error-500-only'
        page.route(error_path,lambda route:route.fulfill(status=500,content_type='text/html',body=error.content))
        for width,height in [(1440,900),(390,844),(320,740)]:
            page.set_viewport_size({'width':width,'height':height});response=page.goto(error_path,wait_until='networkidle')
            page.evaluate('document.fonts.ready');inspect(page,language,'500',width,response.status)
            shot(page,f'{language}-500-{width}')
        context.close()
        print(f'Layout completed: {language}',flush=True)
    page=browser.new_page(viewport={'width':390,'height':844})
    page.goto(BASE+'/cars/',wait_until='networkidle')
    sheet=page.locator('.catalog-sidebar');sheet.locator('summary').click()
    page.wait_for_function("document.querySelector('[data-catalog-filter]').getAttribute('aria-modal')==='true'")
    check('sheet_focus',page.evaluate("document.activeElement.hasAttribute('data-sheet-close')"))
    page.keyboard.press('Escape');page.wait_for_timeout(100)
    check('sheet_escape',not sheet.evaluate('n=>n.open'))
    check('sheet_restore',not page.evaluate("document.querySelector('header').inert"))
    sheet.locator('summary').click();page.wait_for_timeout(150)
    page.locator('[data-sheet-close]').click();check('sheet_close',not sheet.evaluate('n=>n.open'))
    page.set_viewport_size({'width':1440,'height':900});page.goto(BASE+'/cars/',wait_until='networkidle')
    check('all_91_anchors',page.locator('.car-card h3 a').count()==91)
    check('initial_12',page.locator('.car-card:not([hidden])').count()==12)
    page.locator('[data-show-more]').click();check('show_all',page.locator('.car-card:not([hidden])').count()==91)
    page.locator('[data-fleet-sort]').select_option('price')
    prices=page.locator('.car-card:not([hidden])').evaluate_all('nodes=>nodes.map(n=>Number(n.dataset.price))')
    check('sort_price',prices==sorted(prices))
    page.goto(BASE+'/car/lexus-lx-570-superior',wait_until='networkidle')
    page.locator('[data-gallery-next]').click();page.wait_for_timeout(600)
    check('gallery_next',page.locator('.gallery-track').evaluate('n=>n.scrollLeft>0'))
    check('whatsapp_car', 'Lexus' in page.locator('[data-car-wa]').get_attribute('href'))
    page.goto(BASE+'/faq/',wait_until='networkidle')
    faq=page.locator('.faq-list details').first;faq.locator('summary').click();page.wait_for_timeout(450)
    check('faq_open',faq.evaluate('n=>n.open'))
    page.goto(BASE+'/contacts/',wait_until='networkidle');page.keyboard.press('Tab')
    check('skip_link',page.evaluate("document.activeElement.classList.contains('skip-link')"))
    page.keyboard.press('Enter');check('skip_to_main',page.evaluate("document.activeElement.id==='main'"))
    for language in ['ru','kk','en']:
        context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
        static=context.new_page();prefix='' if language=='ru' else '/'+language
        static.goto(BASE+prefix+'/',wait_until='networkidle')
        check(language+'_no_js',static.locator('h1').is_visible() and static.locator('[data-quick-search] button').is_visible() and static.locator('.car-card h3 a').count()>0)
        context.close()
    context=browser.new_context(reduced_motion='reduce',viewport={'width':1440,'height':900})
    static=context.new_page();requests=[];static.on('request',lambda request:requests.append(request.url))
    static.goto(BASE+'/',wait_until='networkidle');static.wait_for_timeout(1500)
    check('reduced_no_video',not any('.mp4' in url or '.glb' in url for url in requests))
    context.close();browser.close()
report['passed']=not report['failures'] and not report['errors']
(ROOT/'reports'/f'night_garage_round{args.round}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'passed':report['passed'],'layouts':len(report['layouts']),'checks':len(report['checks']),'failures':report['failures'],'errors':report['errors']},ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
