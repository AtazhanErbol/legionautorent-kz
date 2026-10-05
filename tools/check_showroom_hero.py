"""Audit chapter pacing, composited contrast, motion and static hero screenshots."""
import io
import json
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/showroom-final'
OUT.mkdir(parents=True, exist_ok=True)
report = {'checks': {}, 'errors': [], 'screens': [], 'flicks': [], 'contrast': [], 'motion': []}

def check(name, ok): report['checks'][name] = bool(ok)
def lum(rgb):
    c = [v/255/12.92 if v/255 <= .04045 else ((v/255+.055)/1.055)**2.4 for v in rgb[:3]]
    return .2126*c[0]+.7152*c[1]+.0722*c[2]

def scroll(page, progress, settle=300):
    page.evaluate('p=>{const h=document.querySelector("[data-mercedes-preview]");scrollTo({top:h.getBoundingClientRect().top+scrollY+p*Math.max(0,h.offsetHeight-innerHeight),behavior:"instant"})}', progress)
    if page.locator('[data-mercedes-preview]').get_attribute('data-mode') == 'cinematic':
        page.wait_for_function('p=>Math.abs(Number(document.querySelector("[data-mercedes-preview]").dataset.progress)-p)<.0005', arg=progress)
    page.wait_for_timeout(settle)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    for width, height in [(1440,900),(390,844),(1366,768),(1920,1080),(1024,768),(768,1024),(320,740)]:
        context = browser.new_context(viewport={'width':width,'height':height}, **({'is_mobile':True,'has_touch':True} if width<900 else {}))
        page = context.new_page();requests=[]
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('request', lambda request: requests.append(request.url))
        page.goto('http://127.0.0.1:8002/',wait_until='networkidle')
        active = width >= 900
        if active: page.wait_for_selector('[data-state=ready]')
        check(f'{width}-single-h1',page.locator('h1').count()==1)
        check(f'{width}-four-SSR-chapters',page.locator('[data-band]').count()==4)
        for progress in [0,.25,.5,.75,1]:
            scroll(page,progress)
            result=page.evaluate('''()=>{
                const root=document.querySelector('[data-mercedes-preview]'),stage=root.firstElementChild,v=root.querySelector('.mercedes-video'),r=v.getBoundingClientRect(),h=root.querySelector('h1');
                const scale=Math.min(r.width/1280,r.height/720),w=1280*scale,ht=720*scale,x=r.x+(r.width-w)/2,y=r.y+(r.height-ht)/2;
                return {scroll:scrollY,mode:root.dataset.mode,progress:root.dataset.progress,time:v.currentTime,videoSize:[v.videoWidth,v.videoHeight],overflow:document.documentElement.scrollWidth>innerWidth,gap:document.querySelector('#fleet').getBoundingClientRect().top-root.getBoundingClientRect().bottom,span:root.offsetHeight-stage.offsetHeight,lastScroll:root.getBoundingClientRect().top+scrollY+root.offsetHeight-stage.offsetHeight,car:{left:x+w*.12,right:x+w*.86,top:y+ht*.31,bottom:y+ht*.79},headlightsTop:y+ht*.48,h1Bottom:h.getBoundingClientRect().bottom,lines:Math.round(h.getBoundingClientRect().height/parseFloat(getComputedStyle(h).lineHeight)),image:root.querySelector('img').currentSrc};
            }''')
            name=f'{width}-{int(progress*100):03}'
            check(name+'-overflow',not result['overflow']);check(name+'-gap',abs(result['gap'])<2)
            if active:
                check(name+'-whole-car',result['car']['left']>=0 and result['car']['right']<=width and result['car']['bottom']<=height)
                check(name+'-native-resolution',result['videoSize']==[1280,720])
                check(name+'-500vh',abs(result['span']-4*height)<2)
                if progress==0:check(name+'-h1-above-headlights',result['h1Bottom']<result['headlightsTop'] and result['lines']<=3)
                if progress==1:check(name+'-rest-frame',abs(result['time']-179/24)<1/24)
            else:
                check(name+'-no-video',not any('.mp4' in u for u in requests))
                check(name+'-static-frame','hero-static-' in result['image'])
            if width in (1440,390,1366,1920):page.screenshot(path=str(OUT/(name+'.png')))
            report['screens'].append({'width':width,'height':height,'requested_progress':progress,**result})
        if width==390:
            page.locator('[data-mercedes-preview]').screenshot(path=str(OUT/'390-hero-complete.png'))
        if width==1440:
            scroll(page,.88);page.screenshot(path=str(OUT/'1440-cta.png'))
            # Inspect the actual composited text backgrounds at four positions per band.
            for index,(start,end) in enumerate([(0,.22),(.23,.54),(.55,.77),(.78,1)]):
                band=page.locator('[data-band]').nth(index)
                text=band.locator('[data-contrast]')
                for fraction in [.08,.35,.65,.92]:
                    phase=start+(end-start)*fraction;scroll(page,phase,80)
                    color=text.evaluate('n=>getComputedStyle(n).color')
                    rgb=[float(v) for v in color.removeprefix('rgb(').removesuffix(')').split(',')]
                    box=text.bounding_box()
                    text.evaluate("n=>{n.style.color='transparent';n.style.textShadow='none'}")
                    screenshot=Image.open(io.BytesIO(page.screenshot())).convert('RGB')
                    text.evaluate("n=>{n.style.removeProperty('color');n.style.removeProperty('text-shadow')}")
                    area=screenshot.crop((max(0,int(box['x'])),max(0,int(box['y'])),min(width,int(box['x']+box['width'])),min(height,int(box['y']+box['height']))))
                    brightest=max(lum(pixel) for pixel in area.getdata())
                    ratio=(lum(rgb)+.05)/(brightest+.05)
                    report['contrast'].append({'band':index+1,'progress':phase,'ratio':round(ratio,3)})
                    check(f'contrast-{index}-{fraction}',ratio>=3.5)
            # Real native scroll at three wheel-equivalent increments, 400 ms pauses.
            span=page.locator('[data-mercedes-preview]').evaluate('n=>n.offsetHeight-n.firstElementChild.offsetHeight')
            for step in [120,240,360]:
                scroll(page,0)
                hits=[0]*4
                for y in range(0,round(span)+1,step):
                    page.evaluate('y=>scrollTo({top:y,behavior:"instant"})',y)
                    page.wait_for_timeout(400)
                    for i,opacity in enumerate(page.locator('[data-band]').evaluate_all('nodes=>nodes.map(n=>Number(getComputedStyle(n).opacity))')):
                        if opacity>=.98:hits[i]+=1
                report['flicks'].append({'step':step,'fully_readable_samples':hits})
                check(f'flick-{step}',all(count>=(5 if step==120 else 1) for count in hits))
            # Quiet performance run: UI FPS is separate from the file's 24 fps.
            scroll(page,0)
            motion=page.evaluate('''()=>new Promise(resolve=>{
                const h=document.querySelector('[data-mercedes-preview]'),v=h.querySelector('video'),span=h.offsetHeight-h.firstElementChild.offsetHeight;
                const frames=[],shown=[];let start,last,done=false;
                function presented(now,m){shown.push({at:now,media:m.mediaTime});if(!done)v.requestVideoFrameCallback(presented)}
                v.requestVideoFrameCallback(presented);
                function tick(now){start??=now;if(last)frames.push(now-last);last=now;let t=Math.min(1,(now-start)/12000);scrollTo({top:span*(t<.5?t*2:(1-t)*2),behavior:'instant'});if(t<1)requestAnimationFrame(tick);else{done=true;resolve({frames,shown})}}
                requestAnimationFrame(tick);
            })''')
            ui=motion['frames'];shown=motion['shown'];unique=[s for i,s in enumerate(shown) if i==0 or s['media']!=shown[i-1]['media']]
            result={'width':width,'height':height,'ui_average_fps':round(1000/(sum(ui)/len(ui)),2),'ui_longest_frame_ms':round(max(ui),2),'ui_frames_over_50ms':sum(v>50 for v in ui),'source_fps':24,'presented_changes':len(unique)}
            report['motion'].append(result);check('motion-55fps',result['ui_average_fps']>=55);check('motion-under-50ms',max(ui)<=50)
            scroll(page,1)
            page.locator('.mercedes-caption--end a[href="#fleet"]').click()
            check('cta-catalog-focus',page.locator('#fleet h2').evaluate('n=>n===document.activeElement'))
            check('cta-catalog-position',abs(page.locator('#fleet').bounding_box()['y']-96)<3)
            page.locator('.partner-section').screenshot(path=str(OUT/'partner.png'))
        context.close()
    # RU/KK/EN captions stay editable/localized; no additional headings are introduced.
    for prefix in ['kk/','en/']:
        page=browser.new_page(viewport={'width':1440,'height':900})
        page.goto('http://127.0.0.1:8002/'+prefix,wait_until='networkidle');page.wait_for_selector('[data-state=ready]')
        for progress in [0,.35,.65,.9]:
            scroll(page,progress)
            check(prefix+str(progress)+'-no-overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        check(prefix+'-one-h1',page.locator('h1').count()==1);page.close()
    browser.close()
report['failed']=[name for name,passed in report['checks'].items() if not passed]
report['passed']=not report['failed'] and not report['errors']
(ROOT/'reports/showroom_browser.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'checks':len(report['checks']),'passed':report['passed'],'failed':report['failed'],'motion':report['motion'],'flicks':report['flicks'],'minimum_contrast':min((v['ratio'] for v in report['contrast']),default=0)},ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
