"""Real Chromium smoke tests for the rebuilt SSR pages and progressive enhancements."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/playwright/rebuild';OUT.mkdir(parents=True,exist_ok=True)
BASE=os.getenv('PREVIEW_URL','http://127.0.0.1:8000')
results=[];errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    for width in [320,375,768,1440,1920]:
        page=browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
        requests=[];page.on('request',lambda r:requests.append(r.url));page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
        response=page.goto(BASE+'/',wait_until='networkidle');assert response.status==200
        overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth');assert not overflow, width
        assert page.locator('h1').count()==1;assert page.locator('.car-card').count()==59
        if width<768:assert not any(('/hero-' in u or '/three-' in u) and u.endswith('.js') or u.endswith('.glb') for u in requests)
        if width==1440:
            page.wait_for_selector('[data-hero][data-state=ready]',timeout=30000)
            assert page.locator('.hero-canvas canvas').count()==1
            page.screenshot(path=str(OUT/'desktop-start.png'))
            canvas=page.locator('.hero-canvas canvas');box=canvas.bounding_box();page.mouse.move(box['x']+box['width']*.7,box['y']+box['height']*.5);page.mouse.down();page.mouse.move(box['x']+box['width']*.85,box['y']+box['height']*.5,steps=8);page.mouse.up()
            page.locator('[data-light-toggle]').click();page.wait_for_timeout(200)
            page.evaluate('window.scrollTo(0,innerHeight*.7+88)');page.wait_for_timeout(1200);page.screenshot(path=str(OUT/'desktop-end.png'))
        if width==375:
            page.screenshot(path=str(OUT/'mobile-start.png'));page.evaluate("window.scrollTo({top:document.querySelector('#fleet').offsetTop,behavior:'instant'})");page.wait_for_timeout(1000);page.wait_for_function("[...document.querySelectorAll('.car-card img')].filter(i=>{const r=i.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0}).every(i=>i.complete&&i.naturalWidth>0)");page.screenshot(path=str(OUT/'mobile-catalog.png'))
        results.append({'width':width,'home_200':True,'overflow':overflow,'cards':59,'mobile_3d_not_loaded':width<768 or None});page.close()
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.goto(BASE+'/cars/',wait_until='networkidle')
    page.locator('[name=q]').fill('Camry');page.locator('[data-catalog-filter] button[type=submit]').click();page.wait_for_url('**/cars/?**');page.wait_for_selector('#catalog-results:not([aria-busy])')
    assert page.locator('.car-card').count()>0
    link=page.locator('.car-info h3 a').first.get_attribute('href');page.goto(BASE+link,wait_until='networkidle');assert page.locator('h1').count()==1
    page.screenshot(path=str(OUT/'car-desktop.png'))
    if page.locator('[data-gallery-next]').count():
        page.locator('[data-gallery-next]').click();page.wait_for_timeout(500);assert page.locator('[data-gallery-count]').inner_text().startswith('2 /')
    panel=page.locator('[data-car-booking]');panel.locator('[name=start_date]').fill('2026-10-10');panel.locator('[name=end_date]').fill('2026-10-13');href=panel.locator('[data-car-wa]').get_attribute('href');assert '2026-10-10' in href and '2026-10-13' in href
    page.set_viewport_size({'width':375,'height':900});page.screenshot(path=str(OUT/'car-mobile.png'));assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.goto(BASE+'/kk'+link,wait_until='networkidle');assert page.locator('html').get_attribute('lang')=='kk'
    page.goto(BASE+'/en/does-not-exist/',wait_until='networkidle');assert 'Page not found' in page.locator('h1').inner_text()
    page.close()
    for reason,script in [('reduced_motion',''),('save_data',"Object.defineProperty(navigator,'connection',{value:{saveData:true}})"),('low_memory',"Object.defineProperty(navigator,'deviceMemory',{value:2})")]:
        context=browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce' if reason=='reduced_motion' else 'no-preference')
        if script:context.add_init_script(script)
        page=context.new_page();requested=[];page.on('request',lambda r:requested.append(r.url));page.goto(BASE+'/',wait_until='networkidle');page.wait_for_timeout(2000)
        assert not any(u.endswith('.glb') or '/three-' in u for u in requested),reason
        assert page.locator('.hero-poster').is_visible();context.close()
    browser.close()
report={'responsive':results,'ajax_catalog':True,'gallery':True,'whatsapp_dates':True,'localized_error':True,'fallbacks':['mobile','reduced_motion','save_data','low_memory'],'errors':errors}
(ROOT/'reports/browser_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report))
if errors:raise SystemExit('Browser errors must be resolved')
