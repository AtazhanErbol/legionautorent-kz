r"""Read-only real-browser QA for the five-scene hero and surrounding UI.

Runs against the existing production preview; only writes its dedicated report
and screenshots. It never modifies the DB, submits lead forms, or opens external
contact links. The 404/save-data fixtures exist only in Playwright contexts.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
READY='[data-hero][data-state=video-ready]'
PANELS={"intro":".hero-copy","about":".story-about","details":".story-details","rear":".hero-end","search":".search-wrap"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default=os.getenv('PREVIEW_URL','http://127.0.0.1:8004'))
    parser.add_argument('--out',type=Path,default=ROOT/'output/playwright/hero-story')
    parser.add_argument('--report',type=Path,default=ROOT/'reports/hero_story_browser.json')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);args.report.parent.mkdir(parents=True,exist_ok=True)
    base=args.base_url.rstrip('/')
    report={'time':datetime.now(timezone.utc).isoformat(),'passed':False,'checks':{},'failures':[],
            'stages':[],'gaps':[],'screenshots':[],'errors':[],'diagnostics':[],'navigation':[],'fallbacks':[],'video_asset':{}}
    def check(name,passed,detail=None):
        report['checks'][name]=bool(passed)
        if not passed:report['failures'].append({'check':name,'detail':detail})
    def shot(page,name):
        path=args.out/(name+'.png');page.screenshot(path=str(path));report['screenshots'].append(str(path))
    def no3d(requests):return not any('.glb' in u or '/three-' in u for u in requests)
    def geometry(page):
        return page.evaluate("""()=>{const h=document.querySelector('[data-hero]'),s=h.parentElement;return {start:s.getBoundingClientRect().top+scrollY,span:s.offsetHeight-h.offsetHeight,pins:document.querySelectorAll('.pin-spacer').length,height:innerHeight}}""")
    def pixels(page):
        return page.evaluate("""()=>{const v=document.querySelector('.hero-video'),c=document.createElement('canvas');c.width=120;c.height=68;const x=c.getContext('2d',{willReadFrequently:true});x.drawImage(v,0,0,c.width,c.height);const d=x.getImageData(0,0,c.width,c.height).data;let h=2166136261;for(let i=0;i<d.length;i++){h^=d[i];h=Math.imul(h,16777619)}return {hash:(h>>>0).toString(16),time:v.currentTime,duration:v.duration,paused:v.paused,seeking:v.seeking,ready:v.readyState}}""")
    def stage(page,p,name,geo,screenshot=True):
        page.evaluate('y=>scrollTo({top:y,behavior:"instant"})',geo['start']+geo['span']*p)
        page.wait_for_function("p=>Math.abs(Number(document.querySelector('[data-hero]').dataset.storyProgress)-p)<.004",arg=p,timeout=15000)
        page.wait_for_function("()=>{const v=document.querySelector('.hero-video');return v&&!v.seeking&&v.readyState>=2}",timeout=15000)
        page.wait_for_timeout(240)
        data=page.evaluate("""()=>{const h=document.querySelector('[data-hero]');return {progress:Number(h.dataset.storyProgress),stage:h.dataset.videoStage,overflow:document.documentElement.scrollWidth>innerWidth,panels:[...h.querySelectorAll('[data-story-panel],.search-wrap')].map(n=>({name:n.dataset.storyPanel||'search',inert:n.inert,aria:n.getAttribute('aria-hidden'),opacity:getComputedStyle(n).opacity,visibility:getComputedStyle(n).visibility,pointerEvents:getComputedStyle(n).pointerEvents,rect:{top:n.getBoundingClientRect().top,bottom:n.getBoundingClientRect().bottom}}))}}""")
        data.update({'name':name,'video':pixels(page)});report['stages'].append(data)
        check(name+'_paused',data['video']['paused']);check(name+'_no_overflow',not data['overflow'])
        for panel in data['panels']:
            if panel['inert']:
                check(name+'_'+panel['name']+'_hidden_accessibility',panel['aria']=='true' and panel['pointerEvents']=='none',panel)
                locator=page.locator(PANELS[panel['name']]).locator('a,button,input,select,textarea').first
                if locator.count():
                    accepted=locator.evaluate('n=>{n.focus({preventScroll:true});return document.activeElement===n}')
                    check(name+'_'+panel['name']+'_cannot_focus',not accepted)
        if screenshot:shot(page,name)
        return data
    def gap(page,name):
        data=page.evaluate("""()=>{const h=document.querySelector('[data-hero]').getBoundingClientRect(),f=document.querySelector('#fleet').getBoundingClientRect(),s=document.querySelector('.search-wrap').getBoundingClientRect();return {scroll:scrollY,heroBottom:h.bottom,fleetTop:f.top,searchBottom:s.bottom,visibleGap:Math.max(0,Math.min(f.top,innerHeight)-Math.max(h.bottom,s.bottom,0)),overflow:document.documentElement.scrollWidth>innerWidth}}""")
        data['name']=name;report['gaps'].append(data);check(name+'_gap',data['visibleGap']<2 and not data['overflow'],data)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            def new(name,width=1440,height=1000,reduced=False,save_data=False,missing=False):
                context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,is_mobile=width<900,has_touch=width<900,reduced_motion='reduce' if reduced else 'no-preference')
                context.add_init_script("window.__storyPlays=0;document.addEventListener('play',e=>{if(e.target.matches?.('.hero-video'))window.__storyPlays++},true)")
                if save_data:context.add_init_script("Object.defineProperty(navigator,'connection',{value:{saveData:true}})")
                if missing:context.route('**/*.mp4',lambda route:route.fulfill(status=404,body='Missing test video',content_type='text/plain'))
                page=context.new_page();requests=[]
                page.on('request',lambda r:requests.append(r.url))
                page.on('pageerror',lambda e:report['errors'].append({'case':name,'message':str(e)}))
                page.on('console',lambda m:report['diagnostics'].append({'case':name,'type':m.type,'message':m.text}) if m.type in ('error','warning') else None)
                response=page.goto(base+'/',wait_until='networkidle');check(name+'_200',response.status==200)
                return context,page,requests
            for width,height in [(1440,1000),(1440,900),(1024,768)]:
                label=f'{width}x{height}';context,page,requests=new(label,width,height)
                page.wait_for_selector(READY,timeout=30000);geo=geometry(page)
                check(label+'_one_pin',geo['pins']==1,geo)
                check(label+'_pin_between_two_and_three_windows',2*height<=geo['span']<=3*height,geo)
                check(label+'_no3d',no3d(requests))
                video=page.locator('.hero-video').evaluate('v=>({url:v.currentSrc,width:v.videoWidth,height:v.videoHeight,duration:v.duration})')
                check(label+'_video_1280x720',video['width']==1280 and video['height']==720,video)
                check(label+'_hashed_video_url',bool(re.search(r'/hero-drive\.[0-9a-f]+\.mp4$',video['url'])),video['url'])
                if not report['video_asset']:
                    response=context.request.get(video['url']);payload=response.body();source=(ROOT/'static/video/hero-drive.mp4').read_bytes()
                    report['video_asset']={**video,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'source_sha256':hashlib.sha256(source).hexdigest()}
                    check('served_video_matches_current_source',response.status==200 and payload==source,report['video_asset'])
                samples=[]
                for value in [0,.12,.33,.58,.82,.96]:samples.append(stage(page,value,f'{label}-p{round(value*100):02}',geo))
                check(label+'_forward_video_times',all(a['video']['time']<=b['video']['time']+.04 for a,b in zip(samples,samples[1:])))
                check(label+'_multiple_decoded_frames',len({x['video']['hash'] for x in samples})>=4)
                stopped=pixels(page);page.wait_for_timeout(500);after=pixels(page)
                check(label+'_stops_when_scrolling_stops',stopped['hash']==after['hash'] and abs(stopped['time']-after['time'])<.01)
                page.locator('.search-wrap [name=city]').focus()
                check(label+'_active_search_accepts_focus',page.locator('.search-wrap [name=city]').evaluate('n=>document.activeElement===n'))
                reverse=stage(page,.33,f'{label}-reverse33',geo,screenshot=False)
                check(label+'_leaving_panel_moves_focus_to_hero',page.locator('[data-hero]').evaluate('n=>document.activeElement===n'))
                check(label+'_reverse_restores_frame',reverse['video']['hash']==samples[2]['video']['hash'])
                for value in [.95,.04,.65,.21,.8,.58]:
                    page.evaluate('y=>scrollTo({top:y,behavior:"instant"})',geo['start']+geo['span']*value);page.wait_for_timeout(20)
                rapid=stage(page,.58,f'{label}-rapid58',geo,screenshot=False)
                check(label+'_rapid_final_frame',rapid['video']['hash']==samples[3]['video']['hash'])
                check(label+'_never_plays',page.evaluate('window.__storyPlays')==0)
                for y in [geo['span']-8,geo['span']+100,geo['span']+500,geo['span']+900]:
                    page.evaluate('y=>scrollTo({top:y,behavior:"instant"})',geo['start']+y);page.wait_for_timeout(200);gap(page,label+'-exit-'+str(round(y)))
                shot(page,label+'-catalog-exit')
                if width==1440 and height==1000:
                    stage(page,0,label+'-before-skip',geo,screenshot=False)
                    page.locator('.hero-copy [data-story-skip]').click();page.wait_for_timeout(180)
                    skip=page.evaluate("""()=>({hash:location.hash,focus:document.activeElement===document.querySelector('#fleet h2'),top:document.querySelector('#fleet').getBoundingClientRect().top})""")
                    check('skip_immediately_focuses_catalog',skip['hash']=='#fleet' and skip['focus'] and -10<=skip['top']<=120,skip)
                    count=page.locator('.car-card').count();check('initial_twelve_visible',page.locator('.car-card:not([hidden])').count()==min(12,count))
                    page.locator('[data-show-more]').click();check('show_more_reveals_all_ssr',page.locator('.car-card:not([hidden])').count()==count)
                    fleet=page.locator('[data-fleet]');chips=fleet.locator('button[data-category]');category=chips.nth(1).get_attribute('data-category');chips.nth(1).click()
                    categories=page.locator('.car-card:not([hidden])').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.category)')
                    check('category_filter',bool(categories) and all(x==category for x in categories),categories)
                    chips.first.click();page.locator('[data-fleet-sort]').select_option('price')
                    prices=page.locator('.car-card:not([hidden])').evaluate_all('(nodes)=>nodes.map(n=>Number(n.dataset.price))');check('price_sort',prices==sorted(prices))
                    # Only local navigation; no WhatsApp/telephone link is opened.
                    card=page.locator('.car-card:not([hidden])').first;card.scroll_into_view_if_needed();page.wait_for_timeout(450)
                    card.screenshot(path=str(args.out/'card-closeup.png'))
                    check('card_contact_links',card.locator('[href^="tel:"]').count()==1 and card.locator('[href^="https://wa.me/"]').count()==1)
                    card.locator('.car-detail-link').click();page.wait_for_load_state('networkidle');check('car_detail_navigation','/car/' in page.url and page.locator('h1').count()==1)
                    back=page.go_back(wait_until='networkidle');page.wait_for_selector(READY,timeout=30000)
                    nav=page.evaluate("""()=>({url:location.href,type:performance.getEntriesByType('navigation')[0]?.type,state:document.querySelector('[data-hero]').dataset.state,videos:document.querySelectorAll('.hero-video').length,pins:document.querySelectorAll('.pin-spacer').length})""")
                    report['navigation'].append(nav);check('real_browser_back_restores_scene',nav['videos']==1 and nav['pins']==1 and nav['state']=='video-ready',nav)
                    geo=geometry(page);stage(page,.96,'search-active',geo,screenshot=False)
                    quick=page.locator('[data-quick-search]');start=(date.today()+timedelta(days=7)).isoformat();end=(date.today()+timedelta(days=10)).isoformat()
                    quick.locator('[name=start_date]').fill(start);quick.locator('[name=end_date]').fill(start);check('dates_reject_equal',not quick.evaluate('f=>f.checkValidity()'))
                    quick.locator('[name=end_date]').fill(end);check('dates_valid_range',quick.evaluate('f=>f.checkValidity()'))
                    quick.locator('[name=category]').select_option(category);quick.locator('button[type=submit]').click();page.wait_for_timeout(550)
                    href=page.locator('.car-card:not([hidden]) [data-event=click_whatsapp]').first.get_attribute('href');check('requested_dates_reach_whatsapp',start in href and end in href)
                    faq=page.locator('.faq-list>details').first;summary=faq.locator('summary');summary.scroll_into_view_if_needed();summary.focus();page.keyboard.press('Enter');page.wait_for_timeout(350)
                    check('faq_keyboard_open',faq.get_attribute('open') is not None);page.keyboard.press('Space');page.wait_for_timeout(350);check('faq_keyboard_close',faq.get_attribute('open') is None)
                    summary.click(click_count=3,delay=25);page.wait_for_timeout(400)
                    faqstate=faq.evaluate('d=>({open:d.open,height:d.style.height,moving:d.classList.contains("faq-is-moving"),inert:d.querySelector(".prose").inert})')
                    check('faq_rapid_clicks_settle',faqstate['open'] and not faqstate['height'] and not faqstate['moving'] and not faqstate['inert'],faqstate)
                    page.locator('.site-footer').scroll_into_view_if_needed();page.wait_for_timeout(500);shot(page,'footer-1440');check('footer_links_available',page.locator('.site-footer a[href]').count()>10)
                    page.set_viewport_size({'width':390,'height':844});page.wait_for_function("!document.querySelector('.hero-video')&&!document.querySelector('.pin-spacer')",timeout=10000)
                    check('resize_mobile_removes_pin',page.locator('.pin-spacer').count()==0)
                    page.evaluate('scrollTo({top:0,behavior:"instant"})');page.set_viewport_size({'width':1440,'height':1000});page.wait_for_selector(READY,timeout=30000)
                    check('resize_desktop_one_pin',page.locator('.pin-spacer').count()==1 and page.locator('.hero-video').count()==1)
                context.close()
            context,page,requests=new('wide1920',1920,1080)
            page.wait_for_selector(READY,timeout=30000);geo=geometry(page)
            for value in [0,.33,.82]:
                name=f'1920x1080-p{round(value*100):02}';stage(page,value,name,geo)
                media=page.locator('.hero-media').evaluate("""n=>{const r=n.getBoundingClientRect(),m=new DOMMatrixReadOnly(getComputedStyle(n).transform);return {width:r.width,height:r.height,scaleX:m.a,scaleY:m.d,skewX:m.b,skewY:m.c,objectFit:getComputedStyle(n.querySelector('video')).objectFit}}""")
                report['stages'][-1]['media']=media
                check(name+'_uniform_scale_no_distortion',abs(media['scaleX']-media['scaleY'])<.001 and abs(media['skewX'])<.001 and abs(media['skewY'])<.001 and media['objectFit']=='contain',media)
                if value==0:check('1920_initial_media_scale_capped',media['width']<=1681,media)
            context.close()
            for name,opts in [('mobile390',{'width':390,'height':844}),('mobile320',{'width':320,'height':740}),('tablet768',{'width':768,'height':900}),('reduced',{'reduced':True}),('save-data',{'save_data':True}),('404',{'missing':True})]:
                context,page,requests=new(name,**opts)
                if name=='404':page.wait_for_selector('[data-hero][data-state=fallback]',timeout=20000)
                else:page.wait_for_timeout(1000)
                check(name+'_no_pin',page.locator('.pin-spacer').count()==0);check(name+'_no_video',page.locator('.hero-video').count()==0);check(name+'_no3d',no3d(requests))
                if name!='404':check(name+'_no_mp4_request',not any('.mp4' in u for u in requests))
                fallback=page.evaluate("""()=>({poster:document.querySelector('.hero-poster').currentSrc,complete:document.querySelector('.hero-poster').complete,overflow:document.documentElement.scrollWidth>innerWidth,panels:[...document.querySelectorAll('[data-story-panel],.hero>.search-wrap')].map(n=>({name:n.dataset.storyPanel||'search',inert:n.inert,hidden:n.getAttribute('aria-hidden'),display:getComputedStyle(n).display,opacity:getComputedStyle(n).opacity,top:n.getBoundingClientRect().top}))})""")
                fallback['case']=name;report['fallbacks'].append(fallback)
                check(name+'_poster_loaded',fallback['complete']);check(name+'_no_overflow',not fallback['overflow'])
                check(name+'_all_static_panels_available',all(not n['inert'] and n['hidden']!='true' and n['display']!='none' and float(n['opacity'])>0 for n in fallback['panels']),fallback)
                shot(page,name+'-first')
                quick=page.locator('[data-quick-search]');quick.scroll_into_view_if_needed();page.wait_for_timeout(200);shot(page,name+'-search')
                check(name+'_search_accessible',quick.locator('button[type=submit]').is_visible() and quick.locator('[name=city]').is_enabled())
                for selector,label in [('.story-about','about'),('.story-details','details'),('.hero-end','rear')]:
                    page.locator(selector).scroll_into_view_if_needed();page.wait_for_timeout(150);shot(page,name+'-'+label)
                check(name+'_flow_order',fallback['panels'][0]['top']<next(n['top'] for n in fallback['panels'] if n['name']=='about')<next(n['top'] for n in fallback['panels'] if n['name']=='details')<next(n['top'] for n in fallback['panels'] if n['name']=='rear'),fallback)
                context.close()
            browser.close()
    except Exception as exc:report['failures'].append({'exception':type(exc).__name__,'message':str(exc)})
    check('no_javascript_errors',not report['errors'],report['errors'])
    report['passed']=not report['failures'];args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'report':str(args.report),'failures':report['failures']},ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__=='__main__':sys.exit(main())
