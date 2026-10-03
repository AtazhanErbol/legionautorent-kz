"""Small release guard tests; existing application tests are left unchanged."""
import json
from bs4 import BeautifulSoup
from django.test import TestCase, override_settings
from cars.models import Car, CarBrand, CarCategory
from core.models import SiteSettings
from locations.models import City
from seo.models import Translation


@override_settings(SECURE_SSL_REDIRECT=False, IS_STAGING=False)
class ReleaseGuardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city=City.objects.create(name='Астана',slug='astana',legacy_path='/',seo_title='Аренда в Астане',seo_description='Автомобили в Астане',seo_h1='ПРОКАТ В АСТАНЕ',canonical_url='https://legionautorent.kz/',body='<p>Условия аренды</p>')
        brand=CarBrand.objects.create(name='Test',slug='test')
        category=CarCategory.objects.create(name='Бизнес',slug='business',seo_title='Бизнес-класс',seo_description='Прокат бизнес-класса',seo_h1='Бизнес-класс')
        cls.car=Car.objects.create(name='Test Car',slug='test-car',legacy_path='/car/test-car',legacy_id='release-guard',brand=brand,category=category,base_price=45000,seo_title='Test Car — аренда',seo_description='Аренда Test Car в Астане',seo_h1='Аренда Test Car',canonical_url='https://legionautorent.kz/car/test-car')
        cls.car.cities.add(cls.city)
        SiteSettings.objects.create(pk=1)

    def soup(self,path):return BeautifulSoup(self.client.get(path).content,'html.parser')

    @override_settings(IS_STAGING=True,ENVIRONMENT='staging')
    def test_nonproduction_has_all_three_robots_guards(self):
        response=self.client.get('/')
        self.assertEqual(response['X-Robots-Tag'],'noindex, nofollow')
        self.assertContains(response,'content="noindex,nofollow"')
        self.assertIn(b'Disallow: /\n',self.client.get('/robots.txt').content)

    @override_settings(ENVIRONMENT='production')
    def test_production_is_indexable_and_has_no_styleguide(self):
        response=self.client.get('/')
        self.assertNotIn('X-Robots-Tag',response)
        self.assertContains(response,'content="index,follow"')
        self.assertNotEqual(self.client.get('/robots.txt').content,b'User-agent: *\nDisallow: /\n')
        for path in ['/styleguide','/styleguide/','/kk/styleguide','/en/styleguide']:
            self.assertEqual(self.client.get(path).status_code,404)

    @override_settings(ENVIRONMENT='development',IS_STAGING=True)
    def test_styleguide_nonproduction_is_noindex_and_not_in_sitemap(self):
        response=self.client.get('/styleguide')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['X-Robots-Tag'],'noindex, nofollow')
        self.assertContains(response,'noindex,nofollow')
        for path in ['/sitemap.xml','/sitemap-pages.xml']:
            self.assertNotIn(b'styleguide',self.client.get(path).content)

    @override_settings(SITE_URL='https://preview.example.test')
    def test_environment_origin_for_canonical_og_and_sitemap(self):
        soup=self.soup('/car/test-car')
        self.assertEqual(soup.select_one('link[rel=canonical]')['href'],'https://preview.example.test/car/test-car')
        self.assertEqual(soup.select_one('meta[property="og:url"]')['content'],'https://preview.example.test/car/test-car')
        self.assertIn('https://preview.example.test/',soup.select_one('meta[property="og:image"]')['content'])
        self.assertIn(b'https://preview.example.test/',self.client.get('/sitemap-cars.xml').content)

    def test_social_tags_and_one_unchanged_h1(self):
        soup=self.soup('/')
        self.assertEqual([x.get_text() for x in soup.select('h1')],['ПРОКАТ В АСТАНЕ'])
        self.assertFalse(soup.select('[data-story-panel] h2'))
        for kind,key in [('property','og:image'),('name','twitter:image'),('name','twitter:title'),('name','twitter:description')]:
            self.assertTrue(soup.find('meta',attrs={kind:key})['content'])

    def test_offer_equals_visible_price(self):
        soup=self.soup('/car/test-car')
        data=[json.loads(n.string) for n in soup.select('script[type="application/ld+json"]')]
        offer=next(x['offers'] for x in data if 'offers' in x)
        self.assertEqual(int(offer['price']),45000)
        self.assertIn('45 000',soup.select_one('.booking-price').get_text())

    def test_filter_canonical_noindex_and_links_in_ssr(self):
        soup=self.soup('/cars/?sort=price')
        self.assertIn('noindex',soup.select_one('meta[name=robots]')['content'])
        self.assertEqual(soup.select_one('link[rel=canonical]')['href'],'https://legionautorent.kz/cars/')
        self.assertTrue(soup.select_one('a[href="/car/test-car"]'))

    def test_incomplete_translation_cannot_be_advertised(self):
        item=Translation.objects.create(content_object=self.car,language='kk',published=True,name='Көлік',title='Көлік',description='Көлік жалдау',h1='Көлік',content='<p>Толық мәтін</p>')
        # Simulate an incomplete imported record, bypassing the admin validator.
        Translation.objects.filter(pk=item.pk).update(content='')
        soup=self.soup('/kk/car/test-car')
        self.assertEqual(soup.html['lang'],'kk')
        self.assertIn('noindex',soup.select_one('meta[name=robots]')['content'])
        self.assertFalse(soup.select('link[hreflang=kk]'))
        self.assertNotIn(b'/kk/car/test-car',self.client.get('/sitemap-cars.xml').content)
        self.assertTrue(soup.select_one('a[href="/en/car/test-car"]'))

    def test_error_is_real_404_and_csp_supports_blob_video(self):
        response=self.client.get('/does-not-exist/')
        self.assertEqual(response.status_code,404)
        self.assertIn("media-src 'self' blob:",response['Content-Security-Policy'])

    def test_head_routes_for_redirect_destination_checks(self):
        for path in ['/','/car/test-car','/cars/','/robots.txt','/sitemap.xml']:
            self.assertEqual(self.client.head(path).status_code,200)
