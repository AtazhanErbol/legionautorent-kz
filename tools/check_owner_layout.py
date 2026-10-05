"""Owner's 7 browser comments and control focus outlines, at reported widths."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/playwright/owner-layout';OUT.mkdir(parents=True,exist_ok=True)
rows=[];errors=[];map_failures=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for width in (825,510,390,1440):
        page=browser.new_page(viewport={'width':width,'height':804 if width!=1440 else 900})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:map_failures.append({'url':r.url,'error':r.failure}) if 'yandex' in r.url else None)
        assert page.goto('http://127.0.0.1:8002/kostanay/?city=kostanay',wait_until='domcontentloaded').status==200
        page.locator('.city-hero-photo img').evaluate('(e)=>e.decode()')
        photo=page.locator('a.city-hero-photo');href=photo.get_attribute('href')
        assert href.startswith('/car/')
        if width==510:
            photo.click();page.wait_for_url('**'+href)
            assert page.locator('.gallery').count()==1
            page.go_back(wait_until='domcontentloaded')
        page.locator('.city-menu summary').screenshot(path=str(OUT/f'city-select-{width}.png'))
        toolbar=page.locator('.fleet-toolbar');toolbar.scroll_into_view_if_needed()
        assert page.locator('.category-chips').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
        page.locator('[data-fleet-sort]').focus()
        assert page.locator('[data-fleet-sort]').evaluate('(e)=>getComputedStyle(e).outlineOffset')=='-2px'
        toolbar.screenshot(path=str(OUT/f'classes-focus-{width}.png'))
        benefits=page.locator('.benefits-grid');benefits.scroll_into_view_if_needed()
        assert benefits.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
        page.wait_for_timeout(600)
        benefits.screenshot(path=str(OUT/f'benefits-{width}.png'))
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        page.goto('http://127.0.0.1:8002/contacts/',wait_until='domcontentloaded')
        page.locator('.map-viewport').scroll_into_view_if_needed()
        page.frame_locator('.map-viewport iframe').get_by_text('Условия использования',exact=True).wait_for(timeout=25000)
        page.wait_for_timeout(1000)
        page.locator('.contact-layout').screenshot(path=str(OUT/f'contacts-map-{width}.png'))
        page.evaluate('scrollTo({top:0,behavior:"instant"})')
        page.screenshot(path=str(OUT/f'contacts-top-{width}.png'))
        gaps=page.evaluate('''()=>{const intro=document.querySelector('.page-content'),contact=document.querySelector('.contact-layout');return {gap:contact.getBoundingClientRect().top-intro.getBoundingClientRect().bottom,overflow:document.documentElement.scrollWidth>innerWidth+1}}''')
        assert gaps['gap']<=50 and not gaps['overflow'],gaps
        rows.append({'width':width,'status':200,'classes_scroll':False,'benefits_scroll':False,'focus_offset':-2,'contacts_gap_px':gaps['gap'],'map_frames':[f.url for f in page.frames if f!=page.main_frame]})
        page.close()
    # Actual filter interaction: expand details first; it is collapsed by design.
    page=browser.new_page(viewport={'width':1440,'height':900});page.goto('http://127.0.0.1:8002/cars/?city=kostanay',wait_until='domcontentloaded')
    page.locator('.catalog-sidebar summary').click()
    page.locator('[data-catalog-filter] select[name=city]').select_option('pavlodar')
    page.locator('[data-catalog-filter] button[type=submit]').click()
    expect(page.locator('[data-city-label]')).to_have_text('Павлодар')
    page.goto('http://127.0.0.1:8002/',wait_until='domcontentloaded')
    assert page.locator('#quick-city').input_value()=='pavlodar'
    assert 'Павлодар' in page.locator('[data-city-label]').inner_text()
    browser.close()
report={'checks':rows,'ajax_city_persisted':True,'js_errors':errors,'map_network_failures':map_failures}
(ROOT/'reports/owner_layout_browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False));assert not errors
