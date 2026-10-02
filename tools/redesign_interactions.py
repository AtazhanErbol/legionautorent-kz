"""Read-only UI interactions: hero controls, dates, SEO disclosure and lazy map."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BASE=os.getenv('PREVIEW_URL','http://127.0.0.1:8004')
result={}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.goto(BASE+'/',wait_until='networkidle');page.wait_for_selector('[data-hero][data-state=ready]')
    assert page.evaluate('document.elementFromPoint(1000,450).tagName')=='CANVAS'
    canvas=page.locator('.hero-canvas canvas');before=canvas.screenshot()
    page.mouse.move(1000,450);page.mouse.down();page.mouse.move(1150,490,steps=10);page.mouse.up();page.wait_for_timeout(200)
    assert before!=canvas.screenshot();result['hero_drag']=True
    button=page.locator('[data-light-toggle]');assert button.get_attribute('aria-pressed')=='false'
    button.click();page.wait_for_timeout(200);assert button.get_attribute('aria-pressed')=='true';result['hero_headlights']=True
    quick=page.locator('[data-quick-search]');quick.locator('[name=start_date]').fill('2026-10-10');quick.locator('[name=end_date]').fill('2026-10-10')
    assert not quick.evaluate('(form)=>form.checkValidity()')
    quick.locator('[name=end_date]').fill('2026-10-13');quick.locator('[name=category]').select_option('business');quick.locator('button').click();page.wait_for_timeout(600)
    assert page.locator('.car-card:not([hidden])').count()>0
    assert all(c=='business' for c in page.locator('.car-card:not([hidden])').evaluate_all('(cards)=>cards.map(c=>c.dataset.category)'))
    href=page.locator('.car-card:not([hidden]) [data-event=click_whatsapp]').first.get_attribute('href');assert '2026-10-10' in href and '2026-10-13' in href
    result['quick_search_dates_and_class']=True
    seo=page.locator('.seo-disclosure');assert seo.locator('.prose').text_content().strip()
    seo.locator('summary').click();assert seo.get_attribute('open') is not None;result['seo_full_dom_and_disclosure']=True
    frame=page.locator('[data-map] iframe');assert not frame.get_attribute('src')
    page.locator('[data-map] summary').click();page.wait_for_timeout(200);assert frame.get_attribute('src')==frame.get_attribute('data-src');result['map_loads_on_request']=True
    page.goto(BASE+'/car/lexus-lx-570-superior',wait_until='networkidle')
    panel=page.locator('[data-car-booking]');panel.locator('[name=start_date]').fill('2026-10-10');panel.locator('[name=end_date]').fill('2026-10-13')
    href=panel.locator('[data-car-wa]').get_attribute('href');assert '2026-10-10' in href and '2026-10-13' in href
    assert page.locator('[data-mobile-wa]').get_attribute('href')==href;result['car_and_mobile_whatsapp_dates']=True
    browser.close()
(ROOT/'reports/redesign_interactions.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
