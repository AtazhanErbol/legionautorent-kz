"""Compare visible frame cadence of the 24-fps and 60-fps showroom derivatives."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/playwright/showroom-smooth'
OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'static/hero/hero-scrub-4836d5f97269.mp4'
CANDIDATE=ROOT/'review/showroom-smooth/hero-60-final.mp4'
report={'runs':[], 'errors':[], 'checks':{}}

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for name,film,fps in [('original24',BASE,24),('smooth60',CANDIDATE,60)]:
        page=browser.new_page(viewport={'width':1440,'height':900})
        page.on('pageerror',lambda e:report['errors'].append(str(e)))
        def html(route):
            response=route.fetch()
            text=response.text()
            import re
            text=re.sub(r'data-fps="\d+"',f'data-fps="{fps}"',text)
            route.fulfill(response=response,body=text)
        page.route('http://127.0.0.1:8002/',html)
        page.route('**/*hero-scrub*.mp4',lambda route:route.fulfill(path=str(film),content_type='video/mp4'))
        page.goto('http://127.0.0.1:8002/',wait_until='networkidle')
        page.wait_for_selector('[data-state=ready]')
        page.wait_for_timeout(600)
        for duration in [8000,16000]:
            page.evaluate('scrollTo({top:0,behavior:"instant"})')
            page.wait_for_timeout(1000)
            trace=page.evaluate('''duration=>new Promise(resolve=>{
                const v=document.querySelector('.mercedes-video'),h=document.querySelector('[data-mercedes-preview]');
                const span=h.offsetHeight-h.firstElementChild.offsetHeight,shown=[],raf=[],seeks=[];
                let start,last,done=false,seekingAt=0,handle;
                const seeking=()=>seekingAt=performance.now(),seeked=()=>seeks.push(performance.now()-seekingAt);
                v.addEventListener('seeking',seeking);v.addEventListener('seeked',seeked);
                function presented(now,m){shown.push({at:now,time:m.mediaTime});if(!done)handle=v.requestVideoFrameCallback(presented)}
                handle=v.requestVideoFrameCallback(presented);
                function tick(now){start??=now;if(last)raf.push(now-last);last=now;
                    const t=Math.min(1,(now-start)/duration);
                    scrollTo({top:span*(t<.5?t*2:(1-t)*2),behavior:'instant'});
                    if(t<1)requestAnimationFrame(tick);else{done=true;v.cancelVideoFrameCallback(handle);
                        v.removeEventListener('seeking',seeking);v.removeEventListener('seeked',seeked);
                        resolve({shown,raf,seeks,width:v.videoWidth,height:v.videoHeight})}}
                requestAnimationFrame(tick);
            })''',duration)
            unique=[s for i,s in enumerate(trace['shown']) if i==0 or s['time']!=trace['shown'][i-1]['time']]
            gaps=[b['at']-a['at'] for a,b in zip(unique,unique[1:])]
            forward=[b['at']-a['at'] for before,a,b in zip(unique,unique[1:],unique[2:]) if (b['time']-a['time'])*(a['time']-before['time'])>0]
            row={'name':name,'source_fps':24,'file_fps':fps,'scroll_duration_ms':duration,'size':[trace['width'],trace['height']],
                 'changed_frames':len(unique),'video_changes_per_second':round(len(unique)/(duration/1000),2),
                 'p95_video_gap_ms':round(sorted(gaps)[int(len(gaps)*.95)],2),
                 'max_video_gap_ms_same_direction':round(max(forward),2),
                 'max_video_gap_ms_including_reversal':round(max(gaps),2),
                 'mean_seek_ms':round(sum(trace['seeks'])/len(trace['seeks']),2),
                 'ui_fps':round(1000/(sum(trace['raf'])/len(trace['raf'])),2),
                 'ui_max_frame_ms':round(max(trace['raf']),2)}
            report['runs'].append(row)
        if name=='smooth60':
            for phase in [0,.25,.5,.75,1]:
                page.evaluate('p=>{const h=document.querySelector("[data-mercedes-preview]");scrollTo({top:p*(h.offsetHeight-h.firstElementChild.offsetHeight),behavior:"instant"})}',phase)
                page.wait_for_timeout(1200)
                page.screenshot(path=str(OUT/f'1440-{int(phase*100):03}.png'))
            before=page.locator('.mercedes-video').evaluate('v=>v.currentTime')
            page.wait_for_timeout(400)
            report['checks']['end-rests']=page.locator('.mercedes-video').evaluate('v=>v.currentTime')==before
            report['checks']['unchanged-layout']=page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.close()
    browser.close()
for duration in [8000,16000]:
    before,after=[r for r in report['runs'] if r['scroll_duration_ms']==duration]
    report['checks'][f'{duration}-more-presented-frames']=after['changed_frames']>before['changed_frames']*1.4
    report['checks'][f'{duration}-lower-p95-gap']=after['p95_video_gap_ms']<before['p95_video_gap_ms']
    report['checks'][f'{duration}-ui-under-50ms']=after['ui_max_frame_ms']<50
report['passed']=all(report['checks'].values()) and not report['errors']
(ROOT/'reports/showroom_smoothing_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
