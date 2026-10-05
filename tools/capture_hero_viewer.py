"""Read-only WebGL inspection of the standalone GLB preview."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/playwright/hero-model';OUT.mkdir(parents=True,exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8005/assets/hero-sedan/viewer.html',wait_until='networkidle')
    page.wait_for_selector('body[data-ready=true]')
    page.add_style_tag(content='.ui,.hint{display:none}')
    page.wait_for_timeout(800)
    page.screenshot(path=str(OUT/'webgl-front.png'))
    data=page.evaluate('''()=>{let v=window.heroViewer;return {drawCalls:v.renderer.info.render.calls,triangles:v.renderer.info.render.triangles,geometries:v.renderer.info.memory.geometries,lights:v.front.length,rear:v.rear.length}}''')
    for name in ['side','rear']:
        page.evaluate('(name)=>document.querySelector(`[data-view="${name}"]`).click()',name)
        page.wait_for_timeout(300);page.screenshot(path=str(OUT/f'webgl-{name}.png'))
    page.evaluate('document.querySelector("#lights").click()');page.wait_for_timeout(200)
    page.screenshot(path=str(OUT/'webgl-rear-lit.png'))
    page.evaluate('document.querySelector("[data-view=front]").click()');page.wait_for_timeout(300)
    page.screenshot(path=str(OUT/'webgl-front-lit.png'))
    page.evaluate('document.querySelector("#studio").click()');page.wait_for_timeout(300)
    page.screenshot(path=str(OUT/'webgl-neutral.png'))
    data['errors']=errors;browser.close()
(ROOT/'assets/hero-sedan/webgl-inspection.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps(data));assert not errors
