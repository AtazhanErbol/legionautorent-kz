"""Separate interaction measurements; Lighthouse does not exercise mobile motion."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
rows=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for width in (1440,390):
        page=browser.new_page(viewport={'width':width,'height':900 if width==1440 else 844},is_mobile=width==390,has_touch=width==390)
        page.goto('http://127.0.0.1:8002/',wait_until='load')
        selector='.mercedes-video' if width==1440 else '.mercedes-mobile-film'
        if width==390:page.evaluate('scrollTo(0,70)')
        page.wait_for_function('(mobile)=>document.querySelector("[data-mercedes-preview]").dataset[mobile?"ambient":"state"]==="ready"',arg=width==390)
        row=page.evaluate('''async ({selector,mobile})=>{
          const v=document.querySelector(selector),root=document.querySelector('[data-mercedes-preview]');
          const distance=root.offsetHeight-root.querySelector('.mercedes-stage').offsetHeight;
          const times=[],presented=[];let previous=0,callback;
          const quality=v.getVideoPlaybackQuality(),start=performance.now();
          const frame=(now)=>{presented.push(now);callback=v.requestVideoFrameCallback(frame);};
          if(v.requestVideoFrameCallback)callback=v.requestVideoFrameCallback(frame);
          await new Promise(resolve=>{const step=now=>{
            if(previous)times.push(now-previous);previous=now;
            const progress=Math.min(1,(now-start)/6000);
            if(!mobile)scrollTo({top:distance*progress,behavior:'instant'});
            if(progress<1)requestAnimationFrame(step);else resolve();
          };requestAnimationFrame(step);});
          if(callback)v.cancelVideoFrameCallback(callback);
          const final=v.getVideoPlaybackQuality();times.sort((a,b)=>a-b);
          return {raf_fps:1000/(times.reduce((a,b)=>a+b,0)/times.length),raf_p95_ms:times[Math.floor(times.length*.95)],presented_fps:presented.length/6,dropped_frames:final.droppedVideoFrames-quality.droppedVideoFrames,total_frames:final.totalVideoFrames-quality.totalVideoFrames,encoded_fps:60,rest_scroll_y:mobile?null:distance,controls:v.controls};
        }''',{'selector':selector,'mobile':width==390})
        if width==1440:
            page.wait_for_timeout(1000)
            row['rest_video_time']=page.locator(selector).evaluate('(v)=>v.currentTime')
            for y in (0,3500,200,3600,0):
                page.evaluate('(y)=>scrollTo({top:y,behavior:"instant"})',y);page.wait_for_timeout(120)
            page.wait_for_timeout(1100)
            row['flick_return_time']=page.locator(selector).evaluate('(v)=>v.currentTime')
            assert row['flick_return_time']<.1
        else:
            # The mobile layout does not pin. These captures document video-time
            # milestones within the full responsive frame, not fake scroll bands.
            for progress in (0,.25,.5,.75,1):
                page.locator(selector).evaluate('(v,p)=>{v.pause();v.currentTime=p*(v.duration-.02)}',progress)
                page.wait_for_timeout(120)
                page.screenshot(path=str(ROOT/f'output/playwright/site-fixes/mobile-frame-{int(progress*100)}.png'))
        row['width']=width;rows.append(row);page.close()
    browser.close()
(ROOT/'reports/final_motion.json').write_text(json.dumps({'environment':'Headless Chrome on this Windows PC, mobile viewport emulation; not physical phone hardware','results':rows},indent=2),encoding='utf8')
print(json.dumps(rows))
