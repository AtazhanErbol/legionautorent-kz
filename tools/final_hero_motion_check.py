"""Actual Chrome scrub timings, uncropped geometry and adversarial scroll checks."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/playwright/final-hero';OUT.mkdir(parents=True,exist_ok=True)
report={'checks':{},'timing':[],'errors':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for width,height in [(1920,1080),(1440,900),(1366,768),(1024,768),(2560,1080)]:
        page=browser.new_page(viewport={'width':width,'height':height})
        page.on('pageerror',lambda e:report['errors'].append(str(e)))
        page.goto('http://127.0.0.1:8002/',wait_until='networkidle')
        page.wait_for_selector('[data-state=ready]');page.wait_for_timeout(900)
        # Native scroll, full forward/reverse path. Measure rAF intervals; this
        # is UI cadence, not a claim that 24-fps source gains 60 unique frames.
        timing=page.evaluate('''()=>new Promise(resolve=>{
          const hero=document.querySelector('[data-mercedes-preview]'),span=hero.offsetHeight-hero.firstElementChild.offsetHeight;
          const intervals=[];let start=0,last=0;
          function frame(now){if(!start)start=now;if(last)intervals.push(now-last);last=now;
            const p=Math.min(1,(now-start)/6000);scrollTo({top:span*(p<.5?p*2:(1-p)*2),behavior:'instant'});
            if(p<1)requestAnimationFrame(frame);else resolve({intervals,span});}
          requestAnimationFrame(frame);
        })''')
        values=timing.pop('intervals');timing.update(width=width,height=height,frames=len(values),average_fps=round(1000/(sum(values)/len(values)),2),longest_frame_ms=round(max(values),2),frames_over_50ms=sum(x>50 for x in values))
        report['timing'].append(timing)
        for progress in [0,.25,.5,.75,1]:
            page.evaluate('y=>scrollTo({top:y,behavior:"instant"})',timing['span']*progress);page.wait_for_timeout(1000)
            layout=page.evaluate('''()=>{const v=document.querySelector('.mercedes-video'),h=document.querySelector('[data-mercedes-preview]'),s=h.firstElementChild;return {fit:getComputedStyle(v).objectFit,overflow:document.documentElement.scrollWidth>innerWidth,videoPaused:v.paused,seeking:v.seeking,progress:Number(h.dataset.progress),stageTop:s.getBoundingClientRect().top,gap:document.querySelector('#fleet').getBoundingClientRect().top-h.getBoundingClientRect().bottom}}''')
            report['checks'][f'{width}_{progress}_uncropped']=layout['fit']=='contain' and not layout['overflow'] and layout['videoPaused'] and not layout['seeking']
            report['checks'][f'{width}_{progress}_pinned_without_gap']=abs(layout['stageTop'])<2 and abs(layout['gap'])<2
            if width in (1440,1366):page.screenshot(path=str(OUT/f'{width}-p{int(progress*100):03}.png'))
        page.evaluate('y=>{scrollTo(0,y);scrollTo(0,0);scrollTo(0,y*.72)}',timing['span']);page.wait_for_timeout(1500)
        time=page.locator('.mercedes-video').evaluate('v=>v.currentTime');page.wait_for_timeout(250)
        report['checks'][f'{width}_flick_stops']=abs(page.locator('.mercedes-video').evaluate('v=>v.currentTime')-time)<.01
        page.close()
    for width,height in [(390,844),(320,740),(1440,600),(768,1024)]:
        page=browser.new_page(viewport={'width':width,'height':height})
        page.goto('http://127.0.0.1:8002/',wait_until='networkidle');page.wait_for_timeout(800)
        report['checks'][f'{width}x{height}_static_no_crop']=page.locator('.mercedes-picture img').evaluate("v=>getComputedStyle(v).objectFit==='contain'")
        for progress in [0,.25,.5,.75,1]:
            if width==390:page.locator('[data-mercedes-preview]').screenshot(path=str(OUT/f'390-p{int(progress*100):03}-static.png'))
        page.close()
    browser.close()
report['passed']=all(report['checks'].values()) and not report['errors']
report['fps_target_met']=all(r['average_fps']>=55 and r['longest_frame_ms']<=50 for r in report['timing'])
(ROOT/'reports/final_hero_motion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
