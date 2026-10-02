"""Render the provided placeholder GLB in the real scene; no reference car imagery."""
import os
from pathlib import Path
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1600,'height':990},device_scale_factor=1)
    page.on('console',lambda msg: print(msg.type,msg.text) if msg.type in ['warning','error'] else None)
    page.goto(os.getenv('PREVIEW_URL','http://127.0.0.1:8000')+'/',wait_until='networkidle')
    page.wait_for_selector('[data-hero][data-state=ready]',timeout=30000)
    page.wait_for_timeout(1000)
    page.add_style_tag(content='.hero-content,.hero-bottom,.hero-shade{display:none!important}')
    data=page.locator('.hero-canvas').screenshot()
    image=Image.open(BytesIO(data)).convert('RGB');image.resize((1600,900)).save(ROOT/'static/img/hero-poster.webp','WEBP',quality=83,method=6)
    print('Rendered poster:',(ROOT/'static/img/hero-poster.webp').stat().st_size)
    browser.close()
