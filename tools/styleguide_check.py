"""Read-only headed Chrome review of the approval-only Django styleguide."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--round',default='1');args=parser.parse_args()
OUT=ROOT/'output/playwright'/('styleguide-round'+args.round);OUT.mkdir(parents=True,exist_ok=True)
report={'round':args.round,'headed_chrome':True,'layouts':[],'errors':[],'checks':{},'screenshots':[]}
def shot(page,name,full=False):
    file=OUT/(name+'.png');page.screenshot(path=str(file),full_page=full);report['screenshots'].append(str(file))
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=False)
    page=browser.new_page()
    page.on('pageerror',lambda e:report['errors'].append(str(e)))
    for w,h in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844),(320,740)]:
        page.set_viewport_size({'width':w,'height':h})
        response=page.goto('http://127.0.0.1:8002/styleguide',wait_until='networkidle')
        page.evaluate('document.fonts.ready');page.wait_for_timeout(400)
        data=page.evaluate('''()=>{
          const items=[...document.querySelector('.header-inner').children].filter(n=>n.getBoundingClientRect().width>0);
          const overlap=[];for(let i=1;i<items.length;i++){if(items[i-1].getBoundingClientRect().right>items[i].getBoundingClientRect().left+1)overlap.push([items[i-1].className,items[i].className]);}
          return {width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth,headerOverlap:overlap,h1:document.querySelectorAll('h1').length,h1Lines:Math.round(document.querySelector('h1').getBoundingClientRect().height/parseFloat(getComputedStyle(document.querySelector('h1')).lineHeight)),fonts:document.fonts.status};
        }''')
        data['status']=response.status;report['layouts'].append(data)
        shot(page,f'first-{w}')
        if w in (1440,390):
            for name,selector in [('card','.car-card'),('controls','#sg-controls'),('type','#sg-type'),('form','.sg-form'),('faq','.faq-list'),('partner','.partner-section')]:
                element=page.locator(selector).first;element.scroll_into_view_if_needed();page.wait_for_timeout(350)
                element.screenshot(path=str(OUT/f'{name}-{w}.png'))
            for image in page.locator('img[loading=lazy]').all():image.scroll_into_view_if_needed()
            page.evaluate('scrollTo({top:0,behavior:"instant"})');page.wait_for_timeout(500)
            shot(page,f'styleguide-{w}-full',True)
        if w==1440:
            page.locator('.car-card').first.hover();page.wait_for_timeout(400);page.locator('.car-card').first.screenshot(path=str(OUT/'card-hover-1440.png'))
            page.locator('.faq-list details').nth(1).locator('summary').click();page.wait_for_timeout(300)
            report['checks']['accordion']=page.locator('.faq-list details').nth(1).evaluate('n=>n.open')
    page.goto('http://127.0.0.1:8002/styleguide',wait_until='networkidle')
    page.keyboard.press('Tab');report['checks']['skip_link']=page.evaluate('document.activeElement.className')=='skip-link'
    page.keyboard.press('Enter');report['checks']['skip_focus_main']=page.evaluate('document.activeElement.id')=='main'
    report['checks']['noindex_header']='noindex' in page.request.get('http://127.0.0.1:8002/styleguide').headers.get('x-robots-tag','')
    context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    static=context.new_page();static.goto('http://127.0.0.1:8002/styleguide',wait_until='networkidle')
    report['checks']['no_js_content']=static.locator('h1').is_visible() and static.locator('.car-card h3 a').count()==1
    context.close();browser.close()
report['passed']=not report['errors'] and all(report['checks'].values()) and all(not r['overflow'] and not r['headerOverlap'] and r['h1']==1 and r['h1Lines']<=3 and r['status']==200 for r in report['layouts'])
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'reports'/f'styleguide_round{args.round}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
