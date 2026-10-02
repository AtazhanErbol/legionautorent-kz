import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright'
OUT.mkdir(parents=True,exist_ok=True)
results = {'viewports': [], 'errors': [], 'pages': [], 'interactions': []}
BASE=os.getenv('PREVIEW_URL','http://127.0.0.1:8000')
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width':1440,'height':1000})
    page = context.new_page()
    page.on('pageerror',lambda error: results['errors'].append(str(error)))
    page.on('console',lambda message: results['errors'].append(message.text) if message.type=='error' else None)
    page.goto(BASE+'/');page.wait_for_load_state('networkidle')
    for width in [320,375,390,430,768,1024,1440,1920]:
        page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(120)
        metrics = page.evaluate('({width:innerWidth, document:document.documentElement.scrollWidth, images:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src), h1:document.querySelectorAll("h1").length})')
        results['viewports'].append(metrics)
        page.screenshot(path=str(OUT/f'home-{width}.png'),full_page=True)
        if width in [390,1440]:page.screenshot(path=str(OUT/f'hero-{width}.png'))
    for path in ['/cars/','/car/toyota-camry-xv-70-prestige-plus','/kostanay/','/booking/','/kz/car/chevrolet-cobalt','/en/cars/']:
        response=page.goto(BASE+path);page.wait_for_load_state('networkidle')
        results['pages'].append({'path':path,'status':response.status,'lang':page.locator('html').get_attribute('lang'),'title':page.title(),'overflow':page.evaluate('document.documentElement.scrollWidth>innerWidth')})
        page.screenshot(path=str(OUT/(path.strip('/').replace('/','-')+'.png')),full_page=True)
    page.goto(BASE+'/car/chevrolet-cobalt');page.wait_for_load_state('networkidle')
    page.get_by_role('link',name='EN',exact=True).click();page.wait_for_load_state('networkidle')
    results['interactions'].append({'language_switch':page.url.endswith('/en/car/chevrolet-cobalt')})
    page.goto(BASE+'/');page.set_viewport_size({'width':390,'height':844});page.wait_for_load_state('networkidle')
    toggle=page.get_by_role('button',name='Открыть меню');toggle.click()
    results['interactions'].append({'mobile_menu_open':toggle.get_attribute('aria-expanded')=='true'})
    page.keyboard.press('Escape');results['interactions'].append({'mobile_menu_closed':toggle.get_attribute('aria-expanded')=='false'})
    page.goto(BASE+'/car/toyota-camry-xv-70-prestige-plus');page.wait_for_load_state('networkidle')
    first=page.locator('#gallery-main').get_attribute('src');page.locator('.gallery-thumb').nth(1).click()
    results['interactions'].append({'gallery_changed':page.locator('#gallery-main').get_attribute('src')!=first})
    browser.close()
(OUT/'browser_report.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(results,ensure_ascii=True))
if results['errors'] or any(x['document']>x['width'] or x['images'] or x['h1']!=1 for x in results['viewports']) or any(x['status']!=200 or x['overflow'] for x in results['pages']) or any(not next(iter(x.values())) for x in results['interactions']):raise SystemExit(1)
