"""Prevent first-paint jumps and retain complete content when the controller fails."""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
report = {'checks': {}, 'cases': []}
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    for case in ['delayed-controller', 'missing-controller']:
        context = browser.new_context(viewport={'width':1440, 'height':900})
        context.add_init_script("window.__shifts=[];new PerformanceObserver(list=>{for(const e of list.getEntries())if(!e.hadRecentInput)__shifts.push(e.value)}).observe({type:'layout-shift',buffered:true})")
        def controller(route):
            if case == 'missing-controller':
                route.fulfill(status=404, body='Simulated controller failure')
            else:
                response = route.fetch()
                time.sleep(1)
                route.fulfill(response=response)
        context.route('**/mercedes-preview-*.js', controller)
        page = context.new_page()
        page.goto('http://127.0.0.1:8002/', wait_until='networkidle')
        root = page.locator('[data-mercedes-preview]')
        if case == 'delayed-controller':
            page.wait_for_selector('[data-state=ready]')
            page.wait_for_timeout(500)
            cls = page.evaluate('__shifts.reduce((sum,n)=>sum+n,0)')
            report['checks']['delayed-controller-cls-under-001'] = cls < .01
            report['checks']['delayed-controller-animated'] = root.get_attribute('data-mode') == 'cinematic'
            report['cases'].append({'case':case, 'cls':cls})
        else:
            report['checks']['failed-controller-complete-static'] = root.get_attribute('data-mode') == 'static'
            report['checks']['failed-controller-h1'] = page.locator('h1').is_visible()
            report['checks']['failed-controller-booking'] = page.locator('[data-quick-search]').is_visible()
            report['checks']['failed-controller-captions'] = all(page.locator('[data-band]').nth(i).is_visible() for i in range(4))
        context.close()
    browser.close()
report['passed'] = all(report['checks'].values())
(ROOT/'reports/showroom_loading.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
