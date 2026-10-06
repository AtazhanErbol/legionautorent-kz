"""Exercise the actual canvas hero, including fallbacks and reversible scrolling."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as BrowserError

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8002')
    args = parser.parse_args()
    output = ROOT / 'output/playwright/hero-60fps'
    output.mkdir(parents=True, exist_ok=True)
    report = {'browsers': [], 'fallbacks': [], 'unavailable_engines': {}, 'real_phones_tested': False}
    with sync_playwright() as playwright:
        for engine in ('chromium', 'firefox', 'webkit'):
            try:
                browser = getattr(playwright, engine).launch(headless=True, timeout=30000, **({'channel':'chrome'} if engine == 'chromium' else {}))
            except BrowserError as error:
                report['unavailable_engines'][engine] = str(error)
                print('Browser unavailable: '+engine,flush=True)
                continue
            for width in (1440, 390):
                options = {'viewport': {'width': width, 'height': 900 if width == 1440 else 844}, 'has_touch': width == 390}
                if engine != 'firefox': options['is_mobile'] = width == 390
                page = browser.new_page(**options)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.add_init_script('''window.heroPaints=[];
                    const original=CanvasRenderingContext2D.prototype.drawImage;
                    CanvasRenderingContext2D.prototype.drawImage=function(...args){
                      const result=original.apply(this,args);
                      if(this.canvas.classList.contains('mercedes-canvas'))window.heroPaints.push(performance.now());
                      return result;
                    };''')
                page.goto(args.base_url+'/', wait_until='networkidle')
                page.wait_for_function('()=>document.querySelector("[data-mercedes-preview]").dataset.state==="ready"')
                root = page.locator('[data-mercedes-preview]')
                geometry = root.evaluate('e=>({start:e.getBoundingClientRect().top+scrollY,distance:e.querySelector(".mercedes-pin").offsetHeight-e.querySelector(".mercedes-stage").offsetHeight})')
                result = {'browser': engine, 'width': width, 'geometry': geometry, 'errors': errors, 'samples': []}
                result['boot'] = page.evaluate('''()=>({packs:performance.getEntriesByType('resource').filter(r=>r.name.includes('.pack')).map(r=>({start_ms:r.startTime,end_ms:r.responseEnd,bytes:r.transferSize})),poster:document.querySelector('.mercedes-picture img').complete,mp4_requested:performance.getEntriesByType('resource').some(r=>r.name.includes('.mp4'))})''')
                for progress in (0, .25, .5, .75, 1):
                    page.evaluate('(y)=>window.scrollTo({top:y,behavior:"instant"})', geometry['start'] + geometry['distance'] * progress)
                    page.wait_for_function('(p)=>Math.abs(+document.querySelector("[data-mercedes-preview]").dataset.progress-p)<.001', arg=progress)
                    info = root.evaluate('e=>({...e.dataset,canvas:e.querySelector("canvas").getBoundingClientRect().toJSON(),horizontalOverflow:document.documentElement.scrollWidth>innerWidth,videoCount:e.querySelectorAll("video").length})')
                    assert not info['horizontalOverflow'] and info['videoCount'] == 0, info
                    assert abs(int(info['frame']) - round(progress * 595)) <= 1, info
                    result['samples'].append(info)
                    page.screenshot(path=str(output/f'{engine}-{width}-{int(progress*100):03}.png'))
                page.evaluate('(y)=>window.scrollTo({top:y,behavior:"instant"})', geometry['start'])
                page.wait_for_function('()=>document.querySelector("[data-mercedes-preview]").dataset.frame==="0"')
                result['reverse_returns_first_frame'] = True
                # Continuous input followed by momentum-like easing, then reverse.
                measurements = page.evaluate('''async ({start,distance})=>{
                    const begin=performance.now();window.heroPaints=[];
                    await new Promise(resolve=>{const frame=now=>{
                      const p=Math.min(1,(now-begin)/6000);scrollTo({top:start+distance*p,behavior:'instant'});
                      if(p<1)requestAnimationFrame(frame);else resolve();};requestAnimationFrame(frame);});
                    return window.heroPaints;
                  }''', geometry)
                intervals = [b-a for a,b in zip(measurements,measurements[1:])]
                result['draws_per_second'] = round(len(measurements)/6,2)
                result['measurement_note'] = 'Full 9.93s source traversed in 6s; headless refresh/render rate, not a guarantee for real phones.'
                result['draw_interval_p95_ms'] = round(sorted(intervals)[int(len(intervals)*.95)],2) if intervals else None
                page.wait_for_function('()=>document.querySelector("[data-mercedes-preview]").dataset.frame==="595"')
                if width == 390 and engine == 'chromium':
                    session = page.context.new_cdp_session(page)
                    page.evaluate('scrollTo({top:0,behavior:"instant"})')
                    page.wait_for_function('()=>document.querySelector("[data-mercedes-preview]").dataset.frame==="0"')
                    session.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[{'x':190,'y':650}]})
                    for step in range(1,12):
                        session.send('Input.dispatchTouchEvent', {'type':'touchMove','touchPoints':[{'x':190,'y':650-step*40}]})
                        page.wait_for_timeout(30)
                    session.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
                    page.wait_for_timeout(600)
                    result['touch_gesture_progress'] = root.get_attribute('data-progress')
                    assert float(result['touch_gesture_progress']) > 0
                    # Visual viewport/address-bar resizing without a layout-width change.
                    before = root.evaluate('e=>e.querySelector(".mercedes-pin").offsetHeight')
                    session.send('Emulation.setPageScaleFactor', {'pageScaleFactor':1.1})
                    page.wait_for_timeout(200)
                    result['visual_viewport_resize_preserves_pin'] = before == root.evaluate('e=>e.querySelector(".mercedes-pin").offsetHeight')
                    assert result['visual_viewport_resize_preserves_pin']
                    session.send('Emulation.setPageScaleFactor', {'pageScaleFactor':1})
                assert not errors, errors
                result['rest_at_scroll_y'] = geometry['start'] + geometry['distance']
                report['browsers'].append(result)
                print(json.dumps({key: result[key] for key in ('browser','width','draws_per_second','rest_at_scroll_y')}),flush=True)
                page.close()
            browser.close()

        browser = playwright.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':390,'height':844})
        held=[]
        page.route('**/*.pack',lambda route:held.append(route))
        page.goto(args.base_url+'/',wait_until='domcontentloaded')
        page.wait_for_function('()=>document.querySelector("[data-mercedes-preview]").dataset.state==="ready"')
        assert page.locator('.mercedes-picture img').evaluate('e=>e.complete&&e.naturalWidth>0')
        assert page.locator('[data-mercedes-preview]').evaluate('e=>Number(e.dataset.loadedPacks||0)===0')
        report['poster_can_paint_before_frame_download'] = True
        for route in held:route.abort()
        page.close()
        for name, options in [('no-js',{'java_script_enabled':False}),('reduced-motion',{'reduced_motion':'reduce'}),('load-failure',{})]:
            page = browser.new_page(viewport={'width':390,'height':844},**options)
            if name == 'load-failure':page.route('**/*.pack',lambda route:route.abort())
            page.goto(args.base_url+'/',wait_until='networkidle')
            root = page.locator('[data-mercedes-preview]')
            assert root.get_attribute('data-mode') == 'static', name
            assert page.locator('h1').is_visible() and page.locator('[data-quick-search]').is_visible()
            assert page.locator('.mercedes-picture img').evaluate('e=>e.complete&&e.naturalWidth>0')
            assert page.locator('.mercedes-picture img').get_attribute('alt')
            page.screenshot(path=str(output/f'fallback-{name}.png'),full_page=False)
            report['fallbacks'].append({'case':name,'passed':True})
            page.close()
        browser.close()
    (ROOT/'reports/hero_frames_browser.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('All available-browser canvas, scroll, and fallback checks passed; inspect unavailable_engines.')


if __name__ == '__main__':main()
