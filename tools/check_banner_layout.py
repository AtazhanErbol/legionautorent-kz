"""Hero viewport, language, whole-car envelope and pin boundary regression checks."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/banner-final'
OUT.mkdir(parents=True, exist_ok=True)
report = {'checks': {}, 'errors': [], 'layouts': []}
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    for lang in ['', 'kk/', 'en/']:
        for width, height in [(1920,1080),(1440,900),(1366,768),(1024,768),(1024,1366),(768,1024),(390,844),(320,740),(1440,600)]:
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.on('pageerror', lambda e: report['errors'].append(str(e)))
            page.goto('http://127.0.0.1:8002/' + lang, wait_until='networkidle')
            active = width >= 900 and height >= 700 and width > height
            if active:
                page.wait_for_selector('[data-state=ready]')
            for phase in ([0,.25,.5,.75,1] if active else [0]):
                page.evaluate('p=>{const h=document.querySelector("[data-mercedes-preview]");scrollTo({top:h.getBoundingClientRect().top+scrollY+p*(h.offsetHeight-h.firstElementChild.offsetHeight),behavior:"instant"})}',phase)
                if active:
                    page.wait_for_function('p=>Math.abs(Number(document.querySelector("[data-mercedes-preview]").dataset.progress)-p)<.002',arg=phase)
                page.wait_for_timeout(120)
                layout = page.evaluate('''()=>{
                    const h=document.querySelector('[data-mercedes-preview]'),s=h.firstElementChild,v=h.querySelector('video'),r=v.getBoundingClientRect(),heading=h.querySelector('h1');
                    const scale=Math.min(r.width/(v.videoWidth||1918),r.height/(v.videoHeight||1080)),w=(v.videoWidth||1918)*scale,ht=(v.videoHeight||1080)*scale;
                    const x=r.x+(r.width-w)/2,y=r.y+(r.height-ht)/2;
                    return {overflow:document.documentElement.scrollWidth>innerWidth,gap:document.querySelector('#fleet').getBoundingClientRect().top-h.getBoundingClientRect().bottom,stageTop:s.getBoundingClientRect().top,lines:Math.round(heading.getBoundingClientRect().height/parseFloat(getComputedStyle(heading).lineHeight)),headingTop:heading.getBoundingClientRect().top,headerBottom:document.querySelector('.site-header').getBoundingClientRect().bottom,carEnvelope:{left:x+w*.17,right:x+w*.8,top:y+ht*.26,bottom:y+ht*.81},height:innerHeight,state:h.dataset.state};
                }''')
                name=f'{lang or "ru"}-{width}x{height}-{phase}'
                report['checks'][name+'-no-overflow']=not layout['overflow']
                report['checks'][name+'-no-gap']=abs(layout['gap'])<2
                if active:
                    box=layout['carEnvelope']
                    report['checks'][name+'-car-inside-screen']=box['left']>=0 and box['right']<=width and box['top']>=0 and box['bottom']<=height
                    report['checks'][name+'-pinned']=abs(layout['stageTop'])<2
                if phase==0:
                    report['checks'][name+'-heading-clear']=layout['headingTop']>=layout['headerBottom'] and layout['lines']<=3
                report['layouts'].append({'case':name,**layout})
                if not lang and width in (1440,1366,390,320):
                    page.screenshot(path=str(OUT/f'{width}x{height}-{int(phase*100):03}.png'))
            page.close()
    browser.close()
report['failed']=[key for key,value in report['checks'].items() if not value]
report['passed']=not report['failed'] and not report['errors']
(ROOT/'reports/banner_layout.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'failed':report['failed'],'errors':report['errors']}))
raise SystemExit(0 if report['passed'] else 1)
