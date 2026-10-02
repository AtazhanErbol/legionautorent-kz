"""Reproducible Chromium visual rounds and progressive UI checks, with live 3D."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
ROUND=os.getenv('VISUAL_ROUND','1');OUT=ROOT/'output/playwright'/f'visual-round-{ROUND}'
OUT.mkdir(parents=True,exist_ok=True)
BASE=os.getenv('PREVIEW_URL','http://127.0.0.1:8004')
report={'round':ROUND,'pages':[],'scroll':[],'checks':{},'errors':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    for width,height in [(1440,1000),(390,844)]:
        page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
        page.on('pageerror',lambda e:report['errors'].append(str(e)))
        for name,path in [('home','/'),('city','/kostanay/'),('car','/car/lexus-lx-570-superior')]:
            response=page.goto(BASE+path,wait_until='networkidle')
            if name=='home' and width==1440:page.wait_for_selector('[data-hero][data-state=ready]',timeout=30000)
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT/f'{name}-{width}.png'))
            metrics=page.evaluate('''({overflow:document.documentElement.scrollWidth>innerWidth,h1:document.querySelectorAll('h1').length,hero:document.querySelector('[data-hero]')?.dataset.state||'poster',cards:document.querySelectorAll('.car-card').length,visibleCards:document.querySelectorAll('.car-card:not([hidden])').length})''')
            report['pages'].append({'name':name,'width':width,'status':response.status,**metrics})
            assert response.status==200 and not metrics['overflow'] and metrics['h1']==1,(name,width,metrics)
            if name=='home':
                if width==1440:
                    # Sample the actual viewport through the pin end. A full-page image alone is misleading.
                    for y in [0,400,740,900,1100,1400]:
                        page.evaluate('(y)=>window.scrollTo({top:y,behavior:"instant"})',y);page.wait_for_timeout(650)
                        sample=page.evaluate('''(()=>{const h=document.querySelector('.hero').getBoundingClientRect(),f=document.querySelector('#fleet').getBoundingClientRect(),s=document.querySelector('.search-wrap').getBoundingClientRect();return {scroll:scrollY,heroBottom:h.bottom,fleetTop:f.top,searchBottom:s.bottom,gap:Math.max(0,f.top-Math.max(h.bottom,s.bottom)),solidHeader:document.querySelector('.site-header').classList.contains('is-scrolled')}})()''')
                        report['scroll'].append(sample)
                        sample['visibleGap']=max(0,min(sample['fleetTop'],height)-max(sample['heroBottom'],sample['searchBottom'],0))
                        assert sample['visibleGap']<2,sample
                        if y in [740,1100]:page.screenshot(path=str(OUT/f'hero-scroll-{y}.png'))
                page.locator('#fleet').scroll_into_view_if_needed();page.wait_for_timeout(800)
                page.locator('.car-card').first.scroll_into_view_if_needed();page.wait_for_timeout(500)
                page.locator('.car-card').first.screenshot(path=str(OUT/f'card-{width}.png'))
                page.screenshot(path=str(OUT/f'fleet-{width}.png'))
                assert page.locator('.car-card:not([hidden])').count()==12
                requested=[];page.on('request',lambda r:requested.append(r.url))
                page.locator('[data-show-more]').click()
                assert page.locator('.car-card:not([hidden])').count()==metrics['cards']
                assert not any('/cars/?' in u for u in requested)
                report['checks'][f'show_more_{width}']=True
                fleet=page.locator('[data-fleet]');fleet.locator('button[data-category]').nth(1).click()
                category=fleet.locator('button[data-category]').nth(1).get_attribute('data-category')
                assert all(c==category for c in page.locator('.car-card:not([hidden])').evaluate_all('(cards)=>cards.map(c=>c.dataset.category)'))
                fleet.locator('button[data-category]').first.click();page.locator('[data-fleet-sort]').select_option('price')
                prices=page.locator('.car-card:not([hidden])').evaluate_all('(cards)=>cards.map(c=>Number(c.dataset.price))');assert prices==sorted(prices)
                report['checks'][f'filter_sort_{width}']=True
                if width==390:
                    page.locator('.mobile-menu>summary').click()
                    assert page.locator('.mobile-menu .language-switch a').count()==3
                    assert all(x['width']>=44 and x['height']>=44 for x in page.locator('.mobile-menu .language-switch a').evaluate_all('(nodes)=>nodes.map(n=>({width:n.offsetWidth,height:n.offsetHeight}))'))
                    page.locator('.mobile-menu>summary').click()
                    report['checks']['mobile_menu_and_language_targets']=True
            if name=='car':
                if page.locator('[data-gallery-next]').count():
                    page.locator('[data-gallery-next]').click();page.wait_for_timeout(500)
                    assert page.locator('[data-gallery-count]').inner_text().startswith('2 /')
                report['checks'][f'gallery_{width}']=True
            # Load images in the twelve visible cards before full-page capture.
            for card in page.locator('.car-card:not([hidden])').all():
                card.scroll_into_view_if_needed();page.wait_for_timeout(70)
            page.evaluate('window.scrollTo({top:0,behavior:"instant"})');page.wait_for_timeout(700)
            page.screenshot(path=str(OUT/f'{name}-{width}-full.png'),full_page=True,style='.car-card{content-visibility:visible!important}.mobile-contact{position:absolute!important}')
            if name=='home':
                for label,selector in [('steps','.steps-section'),('benefits','.benefits-section'),('faq','.faq-section'),('partner','.partner-section'),('contacts','.contacts-section')]:
                    page.locator(selector).scroll_into_view_if_needed();page.wait_for_timeout(150)
                    page.locator(selector).screenshot(path=str(OUT/f'{label}-{width}.png'))
        page.close()
    page=browser.new_page(viewport={'width':390,'height':844})
    for path in ['/cars/','/rental-conditions/','/contacts/','/faq/','/booking/','/callback/','/privacy/','/consent/','/en/cars/','/kk/car/chevrolet-cobalt']:
        response=page.goto(BASE+path,wait_until='networkidle')
        assert response.status==200,(path,response.status)
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),path
    page.goto(BASE+'/cars/',wait_until='networkidle');page.locator('.catalog-sidebar>summary').click()
    page.locator('[name=q]').fill('Camry');page.locator('[data-catalog-filter] button[type=submit]').click()
    page.wait_for_url('**/cars/?**');page.wait_for_selector('#catalog-results:not([aria-busy])')
    assert page.locator('.car-card').count()>0
    assert all('camry' in x.lower() for x in page.locator('.car-card h3').all_text_contents())
    report['checks']['ajax_catalog']=True
    for width in [320,768,1024,1920]:
        page.set_viewport_size({'width':width,'height':900});page.goto(BASE+'/',wait_until='networkidle')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),width
        report['checks'][f'overflow_{width}']=False
    page.close()
    for reason,script in [('reduced_motion',''),('save_data',"Object.defineProperty(navigator,'connection',{value:{saveData:true}})"),('low_memory',"Object.defineProperty(navigator,'deviceMemory',{value:2})")]:
        context=browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce' if reason=='reduced_motion' else 'no-preference')
        if script:context.add_init_script(script)
        page=context.new_page();requested=[];page.on('request',lambda r:requested.append(r.url))
        page.goto(BASE+'/',wait_until='networkidle');page.wait_for_timeout(1200)
        assert not any(u.endswith('.glb') or '/three-' in u for u in requested),reason
        report['checks'][reason+'_fallback']=True
        context.close()
    context=browser.new_context(java_script_enabled=False)
    page=context.new_page();page.goto(BASE+'/cars/',wait_until='networkidle')
    assert page.locator('.car-card:visible').count()==91
    report['checks']['all_91_cars_without_js']=True
    context.close();browser.close()
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=True))
assert not report['errors'],report['errors']
