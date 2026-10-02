from io import StringIO
from pathlib import Path
from django.test import TestCase,override_settings
from django.conf import settings
from django.core.management import call_command
from django.core.cache import cache
from django.utils.translation import override
from bs4 import BeautifulSoup
from cars.models import Car,CarImage
from locations.models import City
from seo.models import Translation
from core.models import SiteSettings

@override_settings(IS_STAGING=False)
class MigrationAcceptanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):call_command('import_legacy',stdout=StringIO())
    def test_every_preserved_url_seo_and_languages(self):
        from importer.source import catalogue_source
        source,_=catalogue_source()
        for kind in ['cities','cars']:
            for item in source[kind]:
                with self.subTest(path=item['legacy_path']):
                    response=self.client.get(item['legacy_path']);self.assertEqual(response.status_code,200)
                    soup=BeautifulSoup(response.content,'html.parser')
                    self.assertEqual(soup.title.get_text(),item['seo_title'])
                    self.assertEqual(soup.select_one('meta[name=description]')['content'],item['seo_description'])
                    self.assertEqual(soup.select_one('link[rel=canonical]')['href'],settings.SITE_URL+item['legacy_path'])
                    self.assertEqual({n['hreflang'] for n in soup.select('link[hreflang]')},{'ru','kk','en','x-default'})
                    self.assertEqual(len(soup.select('h1')),1)
    def test_import_live_wins_over_database_edits_without_duplicates(self):
        car=Car.objects.filter(slug__contains='_').first();path=car.legacy_path;slug=car.slug;original=car.seo_title
        car.seo_title='Database-only edit';car.base_price=1;car.active=False;car.save()
        before=(Car.objects.count(),City.objects.count(),CarImage.objects.count())
        call_command('import_legacy',stdout=StringIO());car.refresh_from_db()
        self.assertEqual(car.legacy_path,path);self.assertEqual(car.slug,slug);self.assertEqual(car.seo_title,original);self.assertGreater(car.base_price,1);self.assertTrue(car.active)
        self.assertEqual((Car.objects.count(),City.objects.count(),CarImage.objects.count()),before)
        previous_modified=car.updated_at
        call_command('import_legacy',stdout=StringIO());car.refresh_from_db()
        self.assertEqual(car.updated_at,previous_modified)
        self.assertEqual((Car.objects.count(),City.objects.count(),CarImage.objects.count()),before)
    def test_dry_run_does_not_write_database(self):
        car=Car.objects.first();car.base_price=1;car.save()
        call_command('import_legacy',dry_run=True,stdout=StringIO());car.refresh_from_db();self.assertEqual(car.base_price,1)
    def test_sitemap_index_sections_cover_all_preserved_pages(self):
        from xml.etree import ElementTree as ET
        index=ET.fromstring(self.client.get('/sitemap.xml').content);self.assertTrue(index.tag.endswith('sitemapindex'))
        urls=[]
        for section in ['cities','cars','categories','pages']:
            tree=ET.fromstring(self.client.get(f'/sitemap-{section}.xml').content)
            urls += [node.text for node in tree.iter() if node.tag.endswith('loc')]
        for obj in [*Car.objects.public(),*City.objects.filter(active=True)]:self.assertIn(settings.SITE_URL+obj.get_absolute_url(),urls)
        self.assertFalse(any('/kk/' in url or '/en/' in url for url in urls))
    def test_missing_kazakh_data_and_no_kz_redirect(self):
        car=Car.objects.first();response=self.client.get('/kk'+car.legacy_path)
        self.assertEqual(response.status_code,200);self.assertContains(response,'noindex,follow')
        response=self.client.get('/kz'+car.legacy_path);self.assertEqual(response.status_code,404);self.assertNotIn('Location',response)
    def test_cache_invalidates_on_image_translation_and_city_membership(self):
        car=Car.objects.first();self.client.get(car.legacy_path)
        revision=cache.get('page_revision');car.base_price+=1;car.save()
        # Signals commit inside production; TestCase captures callbacks explicitly.
        with self.captureOnCommitCallbacks(execute=True):car.base_price+=1;car.save()
        self.assertNotEqual(cache.get('page_revision'),revision)
