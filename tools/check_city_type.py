"""Targeted headed-Chrome recheck after the final city-title fitting correction."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/night-garage-round3'
report = {'scope': 'City headings only; closing corrections from round 3', 'headed_chrome': True, 'layouts': [], 'failures': []}
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=False)
    page = browser.new_page()
    for language in ['ru', 'kk', 'en']:
        prefix = '' if language == 'ru' else '/' + language
        for width, height in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844),(320,740)]:
            page.set_viewport_size({'width': width, 'height': height})
            for name, path in [('city', '/kostanay/'), ('city-east', '/ustkamenogorsk/'), ('city-pavlodar', '/pavlodar/')]:
                response = page.goto('http://127.0.0.1:8002' + prefix + path, wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                row = page.evaluate('''()=>{const h=document.querySelector('h1'),c=getComputedStyle(h);return {
                  lines:Math.round(h.getBoundingClientRect().height/parseFloat(c.lineHeight)),
                  fontSize:c.fontSize,headingWidth:h.clientWidth,viewport:innerWidth,
                  overflow:document.documentElement.scrollWidth>innerWidth,
                  clipped:h.scrollWidth>h.clientWidth+2,text:h.textContent,
                }}''')
                row.update(language=language, page=name, width=width, status=response.status)
                row['passed'] = response.status == 200 and row['lines'] <= 3 and not row['overflow'] and not row['clipped']
                report['layouts'].append(row)
                if not row['passed']: report['failures'].append(row)
                if width in (1440,390):
                    page.screenshot(path=str(OUT / f'{language}-{name}-{width}.png'))
                    if language == 'ru':
                        for section in page.locator('main section').all():
                            section.scroll_into_view_if_needed();page.wait_for_timeout(160)
                        page.evaluate('scrollTo({top:0,behavior:"instant"})');page.wait_for_timeout(250)
                        page.add_style_tag(content='.car-card{content-visibility:visible!important}')
                        page.screenshot(path=str(OUT / f'{language}-{name}-{width}-full.png'), full_page=True)
        print('City typography verified: ' + language, flush=True)
    browser.close()
report['passed'] = not report['failures']
(ROOT / 'reports/night_garage_city_type.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({'checks': len(report['layouts']), 'passed': report['passed'], 'failures': report['failures']}, ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
