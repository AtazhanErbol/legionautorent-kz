"""Real browser checks for the owner's reported bugs. No real leads submitted."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'.local/playwright')
OUT=ROOT/'output/playwright/site-fixes';OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8002'
rows=[];errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for width in (1440,768,390):
        ctx=browser.new_context(viewport={'width':width,'height':900 if width==1440 else 844},is_mobile=width<900,has_touch=width<900)
        page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        for name,path in [('home','/'),('city','/kostanay/'),('contacts','/contacts/'),('privacy','/privacy/'),('car','/car/toyota-land-cruiser-200'),('catalog','/cars/?city=kostanay')]:
            response=page.goto(BASE+path,wait_until='load');assert response.status==200,(name,width,response.status)
            page.wait_for_timeout(450)
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(name,width,'overflow')
            assert page.locator('video[controls],.mercedes-watch').count()==0
            assert page.locator('a[href*="wa.me"]:not([target="_blank"])').count()==0
            if name in ('home','city') and page.locator('[data-mercedes-preview]').count():
                hero=page.locator('[data-mercedes-preview]')
                if width==1440:
                    expect(hero).to_have_attribute('data-state','ready',timeout=25000)
                    scroll=page.locator('.mercedes-preview').evaluate('(e)=>e.offsetHeight-e.querySelector(".mercedes-stage").offsetHeight')
                    for progress in (0,.25,.5,.75,1):
                        page.evaluate('(y)=>scrollTo(0,y)',round(scroll*progress));page.wait_for_timeout(650)
                        page.screenshot(path=str(OUT/f'{name}-{width}-{int(progress*100)}.png'))
                    current=page.locator('.mercedes-video').evaluate('(v)=>v.currentTime')
                    assert current>7,(name,width,current)
                    rows.append({'page':name,'width':width,'scrub_end_time':current,'rest_scroll_y':scroll})
                    page.locator('.mercedes-caption--end a[href="#fleet"]').click()
                    assert page.locator('#fleet').evaluate('(e)=>Math.abs(e.getBoundingClientRect().top-96)<8')
                else:
                    page.evaluate('scrollTo(0,70)')
                    expect(hero).to_have_attribute('data-ambient','ready',timeout=25000)
                    before=page.locator('.mercedes-mobile-film').evaluate('(v)=>v.currentTime')
                    page.wait_for_timeout(800)
                    stats=page.locator('.mercedes-mobile-film').evaluate('(v)=>({time:v.currentTime,paused:v.paused,controls:v.controls,width:v.videoWidth,height:v.videoHeight,fit:getComputedStyle(v).objectFit,quality:v.getVideoPlaybackQuality?.().droppedVideoFrames})')
                    assert stats['time']>before and stats['fit']=='contain' and not stats['controls'],stats
                    rows.append({'page':name,'width':width,'mobile_playback':stats})
                    page.evaluate('scrollTo(0,0)');page.screenshot(path=str(OUT/f'{name}-{width}-animated.png'))
                    page.locator('#fleet').scroll_into_view_if_needed();page.wait_for_timeout(300)
                    assert page.locator('.mercedes-mobile-film').evaluate('(v)=>v.paused')
            if name in ('contacts','privacy','car','catalog'):
                assert 'Костанай' in page.locator('.city-menu summary').inner_text(),(name,width)
            if name=='contacts':
                assert page.locator('[data-request-form] input[name="csrfmiddlewaretoken"]').count()==1
                assert page.locator('[data-request-form] select[name="city"]').input_value()=='2'
                page.locator('.contact-request').screenshot(path=str(OUT/f'contacts-form-{width}.png'))
            if name=='car':
                link=page.locator('[data-gallery-open]').first;link.click()
                assert page.locator('dialog[open]').count()==1
                page.locator('[data-lightbox-image]').evaluate('(v)=>v.decode()')
                page.screenshot(path=str(OUT/f'lightbox-{width}.png'))
                page.keyboard.press('ArrowRight');assert page.locator('[data-lightbox-count]').inner_text().startswith('2 /')
                page.keyboard.press('Escape');assert page.locator('dialog[open]').count()==0
                assert link.evaluate('(e)=>e===document.activeElement')
            page.screenshot(path=str(OUT/f'{name}-{width}.png'),full_page=name in ('contacts','car'))
            rows.append({'page':name,'width':width,'status':200,'overflow':False})
        # City selector can return to Astana and keeps that choice on Contacts.
        page.locator('.city-menu summary').click();page.locator('.city-menu a').filter(has_text='Астана').click()
        page.goto(BASE+'/contacts/');assert 'Астана' in page.locator('.city-menu summary').inner_text()
        ctx.close()
    for gate in ('reduced-motion','save-data','no-js'):
        ctx=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce' if gate=='reduced-motion' else 'no-preference',java_script_enabled=gate!='no-js')
        if gate=='save-data':ctx.add_init_script("Object.defineProperty(navigator,'connection',{value:{saveData:true,effectiveType:'4g'}})")
        page=ctx.new_page();requests=[];page.on('request',lambda r:requests.append(r.url))
        assert page.goto(BASE+'/').status==200;page.evaluate('scrollTo(0,80)') if gate!='no-js' else None
        page.wait_for_timeout(500)
        assert not any('.mp4' in url for url in requests)
        assert page.locator('h1').is_visible()
        rows.append({'gate':gate,'mp4_requested':False,'h1_visible':True});ctx.close()
    browser.close()
(ROOT/'reports/site_fixes_browser.json').write_text(json.dumps({'checks':rows,'js_errors':errors,'live_form_submissions':0},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'checks':len(rows),'errors':errors},ensure_ascii=False));assert not errors
