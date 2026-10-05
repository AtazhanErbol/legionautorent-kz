import tempfile
from pathlib import Path
from io import StringIO
from django.test import TestCase, SimpleTestCase, RequestFactory, override_settings
from django.core.management import call_command, CommandError
from django.http import HttpResponse
from core.middleware import CanonicalHostMiddleware
from bookings.spam import client_ip
from core.models import SiteSettings


class PythonAnywhereHostingTests(SimpleTestCase):
    @override_settings(SECURE_SSL_REDIRECT=True,SECURE_SSL_HOST='legionautorent.kz',CANONICAL_HOST_REDIRECT=True,SITE_URL='https://legionautorent.kz',ALLOWED_HOSTS=['www.legionautorent.kz','legionautorent.kz'])
    def test_http_www_reaches_https_canonical_in_one_hop(self):
        from django.middleware.security import SecurityMiddleware
        app=SecurityMiddleware(CanonicalHostMiddleware(lambda request:HttpResponse('ok')))
        response=app(RequestFactory().get('/car/example?x=1',HTTP_HOST='www.legionautorent.kz'))
        self.assertEqual(response.status_code,301)
        self.assertEqual(response['Location'],'https://legionautorent.kz/car/example?x=1')

    @override_settings(CANONICAL_HOST_REDIRECT=True,SITE_URL='https://legionautorent.kz',ALLOWED_HOSTS=['www.legionautorent.kz','legionautorent.kz'])
    def test_canonical_host_redirect_preserves_path_and_query(self):
        middleware=CanonicalHostMiddleware(lambda request:HttpResponse('ok'))
        request=RequestFactory().get('/cars/?sort=price',HTTP_HOST='www.legionautorent.kz')
        response=middleware(request)
        self.assertEqual(response.status_code,301)
        self.assertEqual(response['Location'],'https://legionautorent.kz/cars/?sort=price')
        self.assertEqual(middleware(RequestFactory().get('/cars/',HTTP_HOST='legionautorent.kz')).status_code,200)

    @override_settings(HOSTING_PLATFORM='pythonanywhere',TRUST_PROXY_HEADERS=True)
    def test_pythonanywhere_uses_only_its_documented_real_ip_header(self):
        request=RequestFactory().get('/',REMOTE_ADDR='10.0.0.4',HTTP_X_REAL_IP='203.0.113.12',HTTP_X_FORWARDED_FOR='1.2.3.4')
        self.assertEqual(client_ip(request),'203.0.113.12')
        request.META['HTTP_X_REAL_IP']='bad,1.2.3.4'
        self.assertEqual(client_ip(request),'10.0.0.4')

    @override_settings(HOSTING_PLATFORM='generic',TRUST_PROXY_HEADERS=True,TRUSTED_PROXY_IPS=['127.0.0.1'])
    def test_generic_host_does_not_trust_unknown_peer(self):
        request=RequestFactory().get('/',REMOTE_ADDR='203.0.113.7',HTTP_X_REAL_IP='1.2.3.4')
        self.assertEqual(client_ip(request),'203.0.113.7')


class PortableExportTests(TestCase):
    def test_export_contains_content_without_credentials_and_detects_damage(self):
        SiteSettings.objects.create()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'content.json'
            call_command('export_pythonanywhere',output=str(path),stdout=StringIO())
            content=path.read_text(encoding='utf8')
            self.assertIn('core.sitesettings',content)
            self.assertNotIn('auth.user',content)
            call_command('import_pythonanywhere',str(path),stdout=StringIO())
            with self.assertRaises(CommandError):call_command('export_pythonanywhere',output=str(path),stdout=StringIO())
            path.write_text(content+' ',encoding='utf8')
            with self.assertRaises(CommandError):call_command('import_pythonanywhere',str(path),stdout=StringIO())
