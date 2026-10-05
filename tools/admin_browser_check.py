"""Local-only authenticated read/interaction check; no CMS submission or credential output."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('DJANGO_SETTINGS_MODULE','legion.settings')
import django;django.setup()
from django.test import Client
from django.conf import settings
from django.contrib.auth import get_user_model
from cars.models import Car
from playwright.sync_api import sync_playwright
base='http://127.0.0.1:8004'
user=get_user_model().objects.filter(is_superuser=True,is_active=True).first()
assert user,'Create a local admin before this check.'
client=Client();client.force_login(user,backend='django.contrib.auth.backends.ModelBackend')
errors=[]
car_id=Car.objects.first().pk
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(viewport={'width':1440,'height':1000})
    context.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':client.cookies[settings.SESSION_COOKIE_NAME].value,'url':base,'httpOnly':True,'sameSite':'Lax'}])
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    for path in [f'core/sitesettings/1/change/',f'cars/car/{car_id}/change/']:
        assert page.goto(base+'/'+settings.ADMIN_PATH+path,wait_until='networkidle').status==200
        tabs=page.locator('.language-editor-tabs');assert tabs.count()==1
        tabs.get_by_role('tab',name='EN',exact=True).click()
        assert page.locator('.translation-inline .inline-related:not(.empty-form):visible select[name$="-language"]').input_value()=='en'
        tabs.get_by_role('tab',name='KZ',exact=True).click()
        assert page.locator('.translation-inline .inline-related:not(.empty-form):visible select[name$="-language"]').input_value()=='kk'
        tabs.get_by_role('tab',name='RU',exact=True).click()
        assert page.locator('.translation-inline .inline-related:not(.empty-form):visible').count()==0
    browser.close()
report={'admin_pages':2,'ru_kk_en_tabs':True,'cms_submissions':0,'errors':errors}
(ROOT/'reports/admin_browser_check.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
assert not errors
