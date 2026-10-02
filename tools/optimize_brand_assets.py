"""Size-only derivatives of original fonts/logo; originals and licenses remain intact."""
import io
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
for name in ['exo2','golos']:
    font=TTFont(ROOT/f'static/fonts/{name}.woff2')
    font.ensureDecompiled()
    if name=='exo2':font=instantiateVariableFont(font,{'wght':600},inplace=True)
    options=subset.Options();options.flavor='woff2';options.layout_features=['*'];options.hinting=False
    sub=subset.Subsetter(options=options)
    sub.populate(unicodes=[*range(0x20,0x100),*range(0x400,0x500),*range(0x2000,0x2070),0x20b8,0x2197,0x2192,0x2212])
    sub.subset(font);font.flavor='woff2';font.save(ROOT/f'static/fonts/{name}-site.woff2')
    glyphs=font.getBestCmap()
    assert all(ord(c) in glyphs for c in 'ӘәҒғҚқҢңӨөҰұҮүҺһІі'),name
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
    page=browser.new_page(viewport={'width':492,'height':171},device_scale_factor=1)
    svg=(ROOT/'static/img/logo.svg').read_text(encoding='utf8').replace('width="1878" height="651"','width="492" height="171"')
    page.set_content('<style>html,body{margin:0;background:transparent}svg{display:block}</style>'+svg)
    page.locator('svg').wait_for();page.wait_for_timeout(300)
    png=page.screenshot(omit_background=True)
    Image.open(io.BytesIO(png)).resize((328,114),Image.Resampling.LANCZOS).save(ROOT/'static/img/logo-site.webp','WEBP',quality=85,method=6)
    browser.close()
for path in [*ROOT.glob('static/fonts/*-site.woff2'),ROOT/'static/img/logo-site.webp']:print(path.name,path.stat().st_size)
