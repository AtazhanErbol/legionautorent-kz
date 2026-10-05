from unittest.mock import patch
from bs4 import BeautifulSoup
from django.core import signing
from django.test import Client, TestCase
from core.models import SiteSettings
from core.templatetags.legion_tags import richtext, map_embed
from urllib.parse import parse_qs, urlsplit
from locations.models import City
from pages.models import Page
from bookings.models import BookingRequest


class SiteFixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.objects.create()
        cls.astana=City.objects.create(name='Астана', slug='astana', legacy_path='/', seo_h1='Аренда в Астане')
        cls.city=City.objects.create(name='Костанай', slug='kostanay', legacy_path='/kostanay/', seo_h1='Аренда в Костанае')
        cls.contacts=Page.objects.create(title='Контакты', slug='contacts', path='/contacts/', seo_h1='Контакты')
        Page.objects.create(title='Политика конфиденциальности', slug='privacy', path='/privacy/', seo_h1='Политика конфиденциальности')

    def test_city_persists_across_sections_languages_and_is_not_shared(self):
        self.client.get('/kostanay/')
        for path in ('/contacts/', '/privacy/', '/en/contacts/', '/'):
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            soup=BeautifulSoup(response.content,'html.parser')
            self.assertIn('Костанай',soup.select_one('.city-menu summary').get_text())
        root=BeautifulSoup(self.client.get('/').content,'html.parser')
        self.assertEqual(root.h1.get_text(),'Аренда в Астане')
        self.assertEqual(root.select_one('#quick-city option[selected]')['value'],'kostanay')
        other=BeautifulSoup(Client().get('/contacts/').content,'html.parser')
        self.assertNotIn('Костанай',other.select_one('.city-menu summary').get_text())
        self.client.get('/?city=astana')
        self.assertEqual(self.client.session['selected_city'],'astana')

    def test_catalog_partial_exposes_selected_city_for_header_update(self):
        response=self.client.get('/cars/',{'city':'kostanay'},HTTP_X_LEGION_PARTIAL='catalog')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['X-Legion-Selected-City'],'kostanay')
        self.assertEqual(self.client.session['selected_city'],'kostanay')
        self.client.get('/contacts/?city=nonexistent')
        self.assertEqual(self.client.session['selected_city'],'kostanay')

    def test_contacts_form_keeps_source_and_selected_city_and_creates_callback(self):
        self.client.get('/kostanay/')
        response=self.client.get('/contacts/')
        form=response.context['form']
        self.assertEqual(form.initial['city'],self.city.pk)
        self.assertEqual(signing.loads(form.initial['source_token'],salt='booking-source'),'/contacts/')
        with patch('core.views.allow_request',return_value=True):
            result=self.client.post('/callback/',{'city':self.city.pk,'name':'Проверка','phone':'+7 700 123 45 67','consent':'on','source_token':form.initial['source_token']})
        self.assertEqual(result.status_code,302)
        lead=BookingRequest.objects.get()
        self.assertEqual((lead.kind,lead.city_id,lead.source_page),('callback',self.city.pk,'/contacts/'))

    def test_contacts_form_csrf_and_invalid_input(self):
        protected=Client(enforce_csrf_checks=True)
        self.assertEqual(protected.post('/callback/',{}).status_code,403)
        with patch('core.views.allow_request',return_value=True):
            self.assertEqual(self.client.post('/callback/',{'phone':'bad'}).status_code,400)
        self.assertEqual(BookingRequest.objects.count(),0)

    def test_all_server_whatsapp_links_and_richtext_open_separately(self):
        soup=BeautifulSoup(self.client.get('/').content,'html.parser')
        links=soup.select('a[href*="wa.me"]')
        self.assertTrue(links)
        for link in links:
            self.assertEqual(link.get('target'),'_blank')
            self.assertIn('noopener',link.get('rel',[]))
        clean=BeautifulSoup(str(richtext('<a href="https://wa.me/77001234567" onclick="bad()">Chat</a><script>bad()</script>')),'html.parser')
        self.assertEqual(clean.a.get('target'),'_blank')
        self.assertFalse(clean.a.has_attr('onclick'))
        self.assertIsNone(clean.script)

    def test_contact_map_uses_city_address_instead_of_shared_legacy_widget(self):
        site=SiteSettings.get_solo()
        site.map_url='https://yandex.ru/map-widget/v1/?um=constructor%3Aastana'
        self.astana.map_url=self.city.map_url=site.map_url
        self.city.address='г. Костанай ул.Дощанова 157 офис 1'
        self.assertEqual(map_embed(self.astana,site),site.map_url)
        params=parse_qs(urlsplit(map_embed(self.city,site)).query)
        self.assertEqual(params['text'],['г. Костанай ул.Дощанова 157'])
        self.city.map_url='https://yandex.ru/map-widget/v1/?um=constructor%3Aunique'
        self.assertEqual(map_embed(self.city,site),self.city.map_url)
