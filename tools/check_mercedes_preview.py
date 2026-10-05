"""Read-only browser check for the current hero and its static fallbacks."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/playwright/mercedes-preview';OUT.mkdir(parents=True,exist_ok=True)
report={'checks':{},'errors':[],'samples':[],'layouts':[]}
def check(name,value):report['checks'][name]=bool(value)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for width,height in [(1920,1080),(1440,900),(1366,768)]:
        context=browser.new_context(viewport={'width':width,'height':height})
        context.add_init_script("window.addEventListener('load',()=>window.__loadedAt=performance.now(),{once:true})")
        page=context.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)))
        response=page.goto('http://127.0.0.1:8002/',wait_until='networkidle')
        page.wait_for_selector('[data-mercedes-preview][data-state=ready]',timeout=30000)
        page.evaluate('document.fonts.ready')
        expected_cars=page.locator('.car-card').count()
        geometry=page.locator('[data-mercedes-preview]').evaluate('n=>({start:n.getBoundingClientRect().top+scrollY,span:n.offsetHeight-n.firstElementChild.offsetHeight})')
        check(f'{width}_200_noindex',response.status==200 and 'noindex' in response.headers.get('x-robots-tag',''))
        check(f'{width}_one_h1',page.locator('h1').count()==1)
        check(f'{width}_400vh',abs(geometry['span']-height*3)<2)
        video=page.locator('.mercedes-video').evaluate('v=>({w:v.videoWidth,h:v.videoHeight,duration:v.duration,src:v.currentSrc})')
        check(f'{width}_motion60_blob',video['w']==1440 and video['h']==810 and video['src'].startswith('blob:') and page.locator('[data-mercedes-preview]').get_attribute('data-fps')=='60')
        timing=page.evaluate("()=>({load:__loadedAt,start:performance.getEntriesByType('resource').find(r=>r.name.includes('mercedes-segment-01')&&r.initiatorType==='fetch')?.startTime})")
        check(f'{width}_video_after_load',timing['start']>=timing['load'])
        samples=[]
        for progress in [0,.25,.5,.75,1,.25]:
            page.evaluate('y=>scrollTo({top:y,behavior:"instant"})',geometry['start']+progress*geometry['span'])
            page.wait_for_function('p=>Math.abs(Number(document.querySelector("[data-mercedes-preview]").dataset.progress)-p)<.002',arg=progress)
            page.wait_for_timeout(300)
            sample=page.evaluate('''()=>{const v=document.querySelector('.mercedes-video'),h=document.querySelector('h1');return {progress:document.querySelector('[data-mercedes-preview]').dataset.progress,time:v.currentTime,paused:v.paused,seeking:v.seeking,overflow:document.documentElement.scrollWidth>innerWidth,h1:h.textContent,headerBottom:document.querySelector('.site-header').getBoundingClientRect().bottom,h1Top:h.getBoundingClientRect().top}}''')
            sample.update(width=width,target=progress);report['samples'].append(sample);samples.append(sample)
            check(f'{width}_{len(samples)}_scroll',not sample['overflow'] and sample['paused'] and not sample['seeking'])
            if len(samples)<=5:page.screenshot(path=str(OUT/f'{width}-p{round(progress*100):03}.png'))
        check(f'{width}_forward',[x['time'] for x in samples[:5]]==sorted(x['time'] for x in samples[:5]))
        check(f'{width}_reverse',abs(samples[-1]['time']-samples[1]['time'])<.05)
        check(f'{width}_header_title',samples[0]['h1Top']>samples[0]['headerBottom'])
        page.locator('.mercedes-bottom a').click();page.wait_for_timeout(250)
        check(f'{width}_catalog_anchor',abs(page.locator('#fleet').bounding_box()['y']-96)<3)
        check(f'{width}_catalog_focus',page.locator('#fleet h2').evaluate('n=>n===document.activeElement'))
        asset=page.locator('[data-mercedes-preview]').get_attribute('data-video')
        partial=context.request.get('http://127.0.0.1:8002'+asset,headers={'Range':'bytes=0-127'})
        check(f'{width}_range',partial.status==206 and len(partial.body())==128)
        context.close()
    for name,width,height,options in [
        ('mobile',390,844,{'is_mobile':True,'has_touch':True}),
        ('narrow',320,740,{'is_mobile':True,'has_touch':True}),
        ('tablet',768,1024,{'is_mobile':True,'has_touch':True}),
        ('reduced',1440,900,{'reduced_motion':'reduce'}),
        ('nojs',1440,900,{'java_script_enabled':False}),
        ('save-data',1440,900,{}),('missing',1440,900,{}),
    ]:
        context=browser.new_context(viewport={'width':width,'height':height},**options)
        if name=='save-data':context.add_init_script("Object.defineProperty(navigator,'connection',{value:{saveData:true}})")
        if name=='missing':context.route('**/*mercedes-segment-01*.mp4',lambda route:route.fulfill(status=404,body='Test only'))
        page=context.new_page();requests=[];page.on('request',lambda r:requests.append(r.url));page.on('pageerror',lambda e:report['errors'].append(str(e)))
        page.goto('http://127.0.0.1:8002/',wait_until='networkidle');page.wait_for_timeout(400)
        check(name+'_static',page.locator('[data-mercedes-preview]').get_attribute('data-state')!='ready')
        check(name+'_h1',page.locator('h1').is_visible())
        check(name+'_search',page.locator('[data-quick-search]').is_visible())
        layout=page.evaluate('''()=>({overflow:document.documentElement.scrollWidth>innerWidth,heroHeight:document.querySelector('[data-mercedes-preview]').offsetHeight,h1Lines:Math.round(document.querySelector('h1').getBoundingClientRect().height/parseFloat(getComputedStyle(document.querySelector('h1')).lineHeight)),cars:document.querySelectorAll('.car-card').length})''')
        layout['case']=name;report['layouts'].append(layout)
        check(name+'_no_overflow',not layout['overflow'])
        check(name+'_preserved_city_cars',layout['cars']==expected_cars)
        check(name+'_h1_at_most_3_lines',layout['h1Lines']<=3)
        if name!='missing':check(name+'_no_video_request',not any('.mp4' in u for u in requests))
        page.screenshot(path=str(OUT/(name+'.png')))
        if name=='mobile':page.locator('[data-mercedes-preview]').screenshot(path=str(OUT/'mobile-hero-full.png'))
        context.close()
    context=browser.new_context(viewport={'width':1440,'height':900})
    page=context.new_page();page.goto('http://127.0.0.1:8002/',wait_until='networkidle');page.wait_for_selector('[data-state=ready]')
    page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(150)
    check('live_reduced_on',page.locator('[data-mercedes-preview]').get_attribute('data-state')=='static')
    page.emulate_media(reduced_motion='no-preference');page.wait_for_selector('[data-state=ready]')
    check('live_reduced_off',page.locator('[data-mercedes-preview]').get_attribute('data-state')=='ready')
    context.close();browser.close()
report['passed']=all(report['checks'].values()) and not report['errors']
report['failed']=[k for k,v in report['checks'].items() if not v]
(ROOT/'reports/mercedes_preview_browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'failed':report['failed'],'errors':report['errors']},ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
