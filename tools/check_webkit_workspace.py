"""Windows WebKit compatibility check; not a physical iPhone/Safari test."""
import os
import sys
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'.local/playwright')
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','legion.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8002'
out=ROOT/'output/playwright/webkit-cms';out.mkdir(parents=True,exist_ok=True)
client=Client();client.force_login(get_user_model().objects.filter(is_superuser=True,is_active=True).first(),backend='django.contrib.auth.backends.ModelBackend')
errors=[];rows=[]
with sync_playwright() as p:
    browser=p.webkit.launch(headless=True)
    for width in (1440,390):
        context=browser.new_context(viewport={'width':width,'height':900 if width==1440 else 844},has_touch=width==390,is_mobile=width==390)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        requests=[];page.on('request',lambda r:requests.append(r.url))
        for name,path in [('home','/'),('city','/kostanay/'),('car','/car/toyota-land-cruiser-200'),('booking','/booking/')]:
            requests.clear()
            response=page.goto(BASE+path,wait_until='load')
            page.wait_for_timeout(900)
            assert response.status==200,(name,response.status)
            overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            assert not overflow,(name,width)
            row={'name':name,'width':width,'status':200,'overflow':False}
            if name=='home':
                row['h264']=page.evaluate('document.createElement("video").canPlayType(\'video/mp4; codecs="avc1.42E01E"\')')
                row['hero_mode']=page.locator('[data-mercedes-preview]').get_attribute('data-mode')
                if width==390:
                    assert row['hero_mode']=='static'
                    assert not any('.mp4' in url for url in requests)
                    page.evaluate('scrollTo(0,70)');page.wait_for_timeout(1500)
                    row['mobile_animation']=page.locator('[data-mercedes-preview]').get_attribute('data-ambient')
                    row['mobile_decode_error']=page.locator('.mercedes-mobile-film').evaluate('(v)=>v.error?.code||null')
                    assert page.locator('video[controls],.mercedes-watch').count()==0
                else:
                    for position in (0,900,1800,2700,3600,0):
                        page.evaluate('(y)=>scrollTo(0,y)',position);page.wait_for_timeout(200)
                row['hero_state']=page.locator('[data-mercedes-preview]').get_attribute('data-state')
                row['decode_failure']=page.locator('[data-mercedes-preview]').get_attribute('data-failure')
            if name=='car':
                page.locator('[data-gallery-open]').first.click()
                assert page.locator('dialog[open]').count()==1
                page.keyboard.press('Escape')
                assert page.locator('dialog[open]').count()==0
            if name=='booking':
                page.locator('input[name="name"]').fill('Проверка формы')
                page.locator('input[name="phone"]').fill('+7 700 123 45 67')
                assert page.locator('input[name="csrfmiddlewaretoken"]').count()==1
            rows.append(row)
            page.screenshot(path=str(out/f'{name}-{width}.png'))
        context.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':client.cookies[settings.SESSION_COOKIE_NAME].value,'url':BASE,'httpOnly':True,'sameSite':'Lax'}])
        for name,path in [('admin',''),('settings','core/sitesettings/1/change/')]:
            response=page.goto(BASE+'/'+settings.ADMIN_PATH+path,wait_until='networkidle')
            assert response.status==200
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            rows.append({'name':name,'width':width,'status':200,'overflow':False})
            if name=='settings':
                page.get_by_role('tab',name='KZ',exact=True).click()
                assert page.locator('.translation-inline .inline-related:not(.empty-form):visible select[name$="-language"]').input_value()=='kk'
            page.screenshot(path=str(out/f'{name}-{width}.png'))
        context.close()
    version=browser.version;browser.close()
report={'engine':'Playwright WebKit '+version+' on Windows','physical_iphone_tested':False,'checks':rows,'errors':errors,'submissions':0}
(ROOT/'reports/webkit_workspace.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False))
assert not errors
