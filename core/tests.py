import json
from datetime import timedelta
from io import StringIO
from xml.etree import ElementTree
from django.test import TestCase, Client, override_settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth import get_user_model
from cars.models import Car, CarBrand, CarCategory, CarPrice
from locations.models import City
from pages.models import Page
from bookings.models import BookingRequest
from seo.models import Redirect, Translation
from core.models import SiteSettings

@override_settings(IS_STAGING=False)
class SiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city=City.objects.create(name='Астана',name_in='Астане',slug='astana',legacy_path='/',seo_title='Аренда авто в Астане',seo_description='Прокат автомобилей',seo_h1='Авто в Астане',body='<p>Астана</p>')
        cls.other=City.objects.create(name='Костанай',slug='kostanay',legacy_path='/kostanay/',seo_title='Авто в Костанае',seo_description='Прокат в Костанае',seo_h1='Аренда в Костанае')
        cls.brand=CarBrand.objects.create(name='Toyota',slug='toyota')
        cls.category=CarCategory.objects.create(name='Бизнес',slug='business',seo_title='Бизнес авто',seo_description='Аренда бизнес',seo_h1='Бизнес')
        cls.car=Car.objects.create(name='Toyota Camry',slug='toyota-camry',legacy_path='/car/toyota-camry',legacy_id='test:1',brand=cls.brand,category=cls.category,base_price=45000,seo_title='Toyota Camry',seo_description='Аренда Camry',seo_h1='Аренда Toyota Camry')
        cls.car.cities.add(cls.city)
        cls.site=SiteSettings.objects.create(pk=1)
        cls.page=Page.objects.create(title='О компании',slug='about',path='/about/',seo_title='О Legion',seo_description='Компания Legion',seo_h1='О компании',body='<p>Legion</p>')
        cls.admin=get_user_model().objects.create_superuser('qa-admin','qa@example.test','test-only-password-52847')
    def payload(self,**changes):
        start=timezone.localdate()+timedelta(days=2)
        result={'name':'QA Tester','phone':'+7 700 123 45 67','city':self.city.pk,'car':self.car.pk,'start_date':start.isoformat(),'end_date':(start+timedelta(days=3)).isoformat(),'consent':'on','source_token':signing.dumps(self.car.legacy_path,salt='booking-source')}
        result.update(changes);return result
    def translated(self, obj=None, language='kk'):
        return Translation.objects.create(content_object=obj or self.car,language=language,published=True,title='Көлікті жалға алу',description='Көлікті жалға алу туралы',h1='Toyota Camry жалдау',content='<p>Қазақша мазмұн</p>',name='Toyota Camry')
    def test_exact_legacy_car_url(self):
        self.assertEqual(self.client.get('/car/toyota-camry').status_code,200)
        self.assertEqual(self.client.get('/car/toyota-camry/').status_code,404)
    def test_root_and_city_paths(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/kostanay/').status_code,200)
        self.assertEqual(self.client.get('/kostanay').status_code,404)
    def test_canonical_and_one_h1(self):
        from bs4 import BeautifulSoup
        soup=BeautifulSoup(self.client.get('/car/toyota-camry').content,'html.parser')
        self.assertEqual(len(soup.select('h1')),1)
        self.assertEqual(soup.select_one('link[rel=canonical]')['href'],'https://legionautorent.kz/car/toyota-camry')
        for node in soup.select('script[type="application/ld+json"]'): self.assertIn('@type',json.loads(node.string))
    def test_hidden_car_returns_404(self):
        self.car.active=False;self.car.save()
        self.assertEqual(self.client.get(self.car.legacy_path).status_code,404)
    def test_hidden_city_returns_404(self):
        self.other.active=False;self.other.save()
        self.assertEqual(self.client.get(self.other.legacy_path).status_code,404)
    def test_filters_noindex_and_base_canonical(self):
        response=self.client.get('/cars/?min_price=20000&q=Camry')
        self.assertContains(response,'noindex,follow')
        self.assertContains(response,'href="https://legionautorent.kz/cars/"')
    def test_untranslated_catalog_not_in_sitemap(self):
        self.assertContains(self.client.get('/en/cars/'),'noindex,follow')
        self.assertNotContains(self.client.get('/sitemap.xml'),'/en/cars/')
    def test_invalid_filter_safe(self):
        response=self.client.get('/cars/?min_price=invalid')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'errorlist')
    def test_no_fake_availability_schema(self):
        response=self.client.get(self.car.legacy_path)
        self.assertNotContains(response,'aggregateRating')
        self.assertNotContains(response,'InStock')
    def test_missing_translation_fallback(self):
        response=self.client.get('/kk'+self.car.legacy_path)
        self.assertContains(response,'<html lang="kk">')
        self.assertContains(response,'noindex,follow')
        self.assertContains(response,'translation-notice')
        self.assertContains(response,'hreflang="kk"')
    def test_draft_translation_not_indexed(self):
        self.translated().delete()
        Translation.objects.create(content_object=self.car,language='en',published=False,title='Draft')
        self.assertContains(self.client.get('/en'+self.car.legacy_path),'noindex,follow')
    def test_published_translation_has_self_canonical(self):
        self.translated()
        response=self.client.get('/kk'+self.car.legacy_path)
        self.assertContains(response,'href="https://legionautorent.kz/kk/car/toyota-camry"')
        self.assertContains(response,'Toyota Camry жалдау')
        self.assertNotContains(response,'class="translation-notice')
        self.assertContains(response,'Қазақша мазмұн')
    def test_translated_og_does_not_fallback_to_ru(self):
        self.car.og_title='Russian OG';self.car.save();self.translated()
        self.assertNotContains(self.client.get('/kk'+self.car.legacy_path),'Russian OG')
    def test_new_city_can_be_added_from_cms(self):
        City.objects.create(name='Новый город',slug='new-city',seo_title='Новый город',seo_description='Прокат',seo_h1='Аренда')
        self.assertEqual(self.client.get('/new-city/').status_code,200)
    def test_hreflang_reciprocal(self):
        self.translated()
        for path in [self.car.legacy_path,'/kk'+self.car.legacy_path]:
            response=self.client.get(path)
            self.assertContains(response,'hreflang="ru"')
            self.assertContains(response,'hreflang="kk"')
            self.assertContains(response,'hreflang="x-default"')
            self.assertNotContains(response,'hreflang="kz"')
    def test_language_switch_same_page(self):
        self.assertContains(self.client.get(self.car.legacy_path),'href="/en/car/toyota-camry"')
    def test_translation_requires_complete_content(self):
        with self.assertRaises(ValidationError): Translation(content_object=self.car,language='en',published=True,title='Title').full_clean()
    def test_sitemap_only_published_translations(self):
        response=self.client.get('/sitemap.xml')
        ElementTree.fromstring(response.content)
        self.assertNotContains(response,'/kk/car/toyota-camry')
        self.translated()
        self.assertContains(self.client.get('/sitemap-cars.xml'),'/kk/car/toyota-camry')
    def test_hidden_objects_excluded_sitemap(self):
        self.car.active=False;self.car.save()
        self.assertNotContains(self.client.get('/sitemap.xml'),self.car.legacy_path)
    def test_production_robots(self):
        response=self.client.get('/robots.txt')
        self.assertContains(response,'Sitemap: https://legionautorent.kz/sitemap.xml')
        self.assertNotContains(response,'Disallow: /\n')
    @override_settings(IS_STAGING=True)
    def test_staging_robots_and_header(self):
        self.assertContains(self.client.get('/robots.txt'),'Disallow: /\n')
        self.assertEqual(self.client.get('/')['X-Robots-Tag'],'noindex, nofollow')
    def test_redirect_301_single_hop(self):
        Redirect.objects.create(old_path='/old-camry',new_path=self.car.legacy_path)
        response=self.client.get('/old-camry')
        self.assertEqual(response.status_code,301);self.assertEqual(response['Location'],self.car.legacy_path)
    def test_redirect_blocks_external_loop_chain(self):
        for path in ['https://example.com','//evil.test/','/bad?foo=bar','/bad\\path']:
            with self.assertRaises(ValidationError):Redirect(old_path='/old',new_path=path).full_clean()
        with self.assertRaises(ValidationError):Redirect(old_path='/same',new_path='/same').full_clean()
        Redirect.objects.create(old_path='/a',new_path='/b')
        for old,new in [('/b','/a'),('/b','/c'),('/z','/a')]:
            with self.assertRaises(ValidationError):Redirect(old_path=old,new_path=new).full_clean()
    def test_csrf_enforced(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/booking/',self.payload()).status_code,403)
    def test_valid_request_with_real_csrf(self):
        from bs4 import BeautifulSoup
        client=Client(enforce_csrf_checks=True)
        response=client.get('/booking/?car='+str(self.car.pk))
        token=BeautifulSoup(response.content,'html.parser').select_one('[name=csrfmiddlewaretoken]')['value']
        data=self.payload();data['csrfmiddlewaretoken']=token
        self.assertEqual(client.post('/booking/',data).status_code,302)
    def test_valid_request_utm_and_source(self):
        self.client.get(self.car.legacy_path+'?utm_source=test&utm_campaign=migration')
        response=self.client.post('/booking/',self.payload())
        self.assertEqual(response.status_code,302)
        lead=BookingRequest.objects.get();self.assertEqual(lead.utm_source,'test');self.assertEqual(lead.utm_campaign,'migration')
        self.assertEqual(lead.source_page,self.car.legacy_path);self.assertTrue(lead.consent)
        self.assertContains(self.client.get('/request-success/'),'data-page-event="booking_submit"')
        self.assertNotContains(self.client.get('/request-success/'),'data-page-event="booking_submit"')
    def test_invalid_phone(self):
        self.assertEqual(self.client.post('/booking/',self.payload(phone='bad')).status_code,400)
        self.assertFalse(BookingRequest.objects.exists())
    def test_missing_consent(self):
        data=self.payload();data.pop('consent')
        self.assertEqual(self.client.post('/booking/',data).status_code,400)
    def test_bad_date_order(self):
        data=self.payload();data['end_date']=data['start_date']
        self.assertEqual(self.client.post('/booking/',data).status_code,400)
    def test_optional_dates(self):
        self.assertEqual(self.client.post('/booking/',self.payload(start_date='',end_date='')).status_code,302)
    def test_translated_form_city_choice(self):
        Translation.objects.create(content_object=self.city,language='en',published=True,name='Astana',title='Car rental in Astana',description='Car hire',h1='Car rental',content='<p>Car rental in Astana</p>')
        self.assertContains(self.client.get('/en/booking/'),'>Astana</option>')
    def test_city_car_mismatch(self):
        self.assertEqual(self.client.post('/booking/',self.payload(city=self.other.pk)).status_code,400)
    def test_honeypot(self):
        self.assertEqual(self.client.post('/booking/',self.payload(website='spam.test')).status_code,400)
        self.assertFalse(BookingRequest.objects.exists())
    def test_signed_source(self):
        self.assertEqual(self.client.post('/booking/',self.payload(source_token='fake')).status_code,400)
    def test_rate_limit(self):
        for i in range(5):self.assertEqual(self.client.post('/booking/',self.payload(phone='bad')).status_code,400)
        self.assertEqual(self.client.post('/booking/',self.payload()).status_code,429)
    def test_partner_settings_and_whatsapp(self):
        self.site.partner_whatsapp='77000000000';self.site.partner_whatsapp_message='Тест партнёра';self.site.save()
        response=self.client.get('/')
        self.assertContains(response,'Стать партнером Легионавто');self.assertContains(response,'https://wa.me/77000000000?text=')
        self.assertNotContains(response,'InvestorApplication')
        self.site.show_partner_section=False;self.site.save()
        self.assertNotContains(self.client.get('/'),'Стать партнером Легионавто')
    def test_partner_translation_message(self):
        Translation.objects.create(content_object=self.site,language='en',published=True,hero_title='Cars',hero_text='Rent a car',partner_title='Partner with Legion',partner_description='Provide your car for sublease.',partner_whatsapp_message='Hello partnership',footer_text='Your plans')
        response=self.client.get('/en/')
        self.assertContains(response,'Partner with Legion');self.assertContains(response,'Hello%20partnership')
    def test_no_investor_routes(self):
        self.assertEqual(self.client.get('/investors/').status_code,404)
        self.assertEqual(self.client.get('/partners/').status_code,404)
    def test_admin_access(self):
        self.client.force_login(self.admin,backend='django.contrib.auth.backends.ModelBackend')
        for path in ['/control-legion/','/control-legion/cars/car/','/control-legion/core/sitesettings/1/change/','/control-legion/bookings/bookingrequest/']:
            self.assertEqual(self.client.get(path).status_code,200)
    def test_tariff_overlap(self):
        CarPrice.objects.create(car=self.car,min_days=1,max_days=3,daily_price=45000)
        with self.assertRaises(ValidationError):CarPrice(car=self.car,min_days=3,max_days=7,daily_price=40000).full_clean()
    def test_sanitized_cms_html(self):
        self.page.body='<p>Good</p><script>alert(1)</script><a href="javascript:alert(1)">Bad</a>';self.page.save()
        response=self.client.get('/about/')
        self.assertNotContains(response,'<script>alert(1)');self.assertNotContains(response,'href="javascript:')
    def test_custom_404_status(self):
        response=self.client.get('/does-not-exist/')
        self.assertEqual(response.status_code,404);self.assertContains(response,'error-code',status_code=404)
    def test_catalog_queries_do_not_grow_per_car(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        # Warm the shared language cache in both cases: measure growth, not cache setup.
        self.client.get('/cars/')
        with CaptureQueriesContext(connection) as small:self.client.get('/cars/')
        for i in range(12):
            car=Car.objects.create(name=f'Toyota {i}',slug=f'toyota-{i}',legacy_path=f'/car/toyota-{i}',legacy_id=f'test:{i+2}',brand=self.brand,category=self.category,base_price=20000)
            car.cities.add(self.city)
        self.client.get('/cars/')
        with CaptureQueriesContext(connection) as queries:self.client.get('/cars/')
        self.assertLessEqual(len(queries),len(small)+2)
        self.assertLess(len(queries),40)

    def test_uploaded_palette_png_preserves_alpha_and_builds_card_variants(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from cars.models import CarImage
        from io import BytesIO
        image=Image.new('P',(900,900),0)
        image.putpalette([0,0,0,255,0,0]+[0]*762)
        image.info['transparency']=0
        image.paste(1,(100,100,800,800))
        original=BytesIO();image.save(original,'PNG')
        with tempfile.TemporaryDirectory() as media,override_settings(MEDIA_ROOT=media):
            photo=CarImage.objects.create(car=self.car,original=SimpleUploadedFile('palette.png',original.getvalue(),content_type='image/png'))
            for field in ['image','small','card_image','card_small']:
                self.assertTrue(Path(getattr(photo,field).path).is_file())
                with Image.open(getattr(photo,field).path) as derived:
                    self.assertIn('A',derived.getbands())
                    self.assertEqual(derived.getpixel((0,0))[3],0)
            self.assertAlmostEqual(photo.card_width/photo.card_height,1.55,places=2)

class ImportTests(TestCase):
    def test_snapshot_import_idempotent_and_preserves_edits(self):
        output=StringIO()
        call_command('migrate_legion_data',stdout=output)
        self.assertEqual(Car.objects.count(),91);self.assertEqual(City.objects.count(),4)
        car=Car.objects.first();car.name='Edited name';car.save()
        call_command('migrate_legion_data',stdout=output)
        self.assertEqual(Car.objects.count(),91);car.refresh_from_db();self.assertEqual(car.name,'Edited name')
    def test_import_dry_run(self):
        call_command('migrate_legion_data',dry_run=True,stdout=StringIO())
        self.assertEqual(Car.objects.count(),0)
