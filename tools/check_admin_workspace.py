"""Read-only visual/keyboard checks against the local preview (no CMS saves)."""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legion.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings
from cars.models import Car
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8002'
user = get_user_model().objects.filter(is_superuser=True, is_active=True).first()
client = Client()
client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
car_id = Car.objects.first().pk
out = ROOT / 'output/playwright/admin-cms'
out.mkdir(parents=True, exist_ok=True)
errors, checks = [], []
pages = [('dashboard', ''), ('cars', 'cars/car/'), ('settings', 'core/sitesettings/1/change/'), ('car', f'cars/car/{car_id}/change/'), ('texts', 'core/interfacetext/'), ('sections', 'core/sitesection/'), ('leads', 'bookings/bookingrequest/')]
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context()
    context.add_cookies([{'name':settings.SESSION_COOKIE_NAME, 'value':client.cookies[settings.SESSION_COOKIE_NAME].value, 'url':BASE, 'httpOnly':True, 'sameSite':'Lax'}])
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    for width in (1440, 768, 390):
        page.set_viewport_size({'width':width, 'height':1000 if width == 1440 else 844})
        for name, path in pages:
            response = page.goto(BASE + '/' + settings.ADMIN_PATH + path, wait_until='networkidle')
            assert response.status == 200, (name, response.status)
            overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            checks.append({'page':name, 'width':width, 'status':200, 'overflow':overflow})
            page.screenshot(path=str(out / f'{name}-{width}.png'), full_page=name=='dashboard')
            assert not overflow, (name, width)
            if width == 390 and name == 'dashboard':
                page.get_by_role('button', name='Разделы', exact=True).click()
                assert page.locator('.cms-nav nav').is_visible()
                page.get_by_role('button', name='Разделы', exact=True).click()
            if name in ('settings','car'):
                tabs=page.locator('.language-editor-tabs')
                for label,language in [('EN','en'),('KZ','kk')]:
                    tabs.get_by_role('tab',name=label,exact=True).click()
                    assert page.locator('.translation-inline .inline-related:not(.empty-form):visible select[name$="-language"]').input_value()==language
                tabs.get_by_role('tab',name='RU',exact=True).click()
    page.set_viewport_size({'width':1440, 'height':1000})
    page.goto(BASE + '/' + settings.ADMIN_PATH, wait_until='networkidle')
    page.locator('[data-nav-search]').fill('Тексты')
    assert page.locator('.cms-nav nav a:visible').count()==1
    # Login remains a standard CSRF-protected form.
    anonymous=browser.new_context(viewport={'width':390,'height':844})
    login=anonymous.new_page()
    assert login.goto(BASE + '/' + settings.ADMIN_PATH + 'login/',wait_until='networkidle').status==200
    assert login.locator('input[name="csrfmiddlewaretoken"]').count()==1
    login.screenshot(path=str(out/'login-390.png'), full_page=True)
    assert not login.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
    browser.close()
report={'checks':checks,'js_errors':errors,'cms_submissions':0}
(ROOT/'reports/admin_workspace_browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
assert not errors
