import json
import re
import struct
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory, override_settings
from django.utils.translation import override
from core.models import SiteSettings
from core.validators import validate_glb
from core.views import server_error


class ReleaseTests(TestCase):
    def test_csp_nonce_is_fresh_even_when_context_is_cached(self):
        SiteSettings.objects.create(pk=1)
        responses=[self.client.get('/cars/') for _ in range(2)]
        nonces=[]
        for response in responses:
            nonce=re.search(r"'nonce-([^']+)'",response['Content-Security-Policy'])[1]
            nonces.append(nonce)
            self.assertNotIn("'unsafe-eval'",response['Content-Security-Policy'])
            self.assertContains(response,f'nonce="{nonce}"')
        self.assertNotEqual(*nonces)

    def test_500_has_no_database_dependency_in_all_languages(self):
        for lang in ['ru','kk','en']:
            request=RequestFactory().get('/'+lang+'/');request.LANGUAGE_CODE=lang
            with override(lang),patch('django.db.backends.utils.CursorWrapper.execute',side_effect=RuntimeError('DB unavailable')):
                response=server_error(request)
            self.assertEqual(response.status_code,500)
            self.assertIn(f'lang="{lang}"'.encode(),response.content)
            self.assertNotIn(b'DB unavailable',response.content)

    def test_glb_rejects_wrong_version_and_length(self):
        for header in [b'glTF'+struct.pack('<II',1,12),b'glTF'+struct.pack('<II',2,123)]:
            with self.assertRaises(ValidationError):validate_glb(SimpleUploadedFile('test.glb',header))
        validate_glb(SimpleUploadedFile('test.glb',b'glTF'+struct.pack('<II',2,12)))

    def test_original_media_urls_and_unrecognized_paths(self):
        response=self.client.get('/img/legionautorent.svg');self.assertEqual(response.status_code,200)
        manifest=json.loads((settings.BASE_DIR/'migration/media_manifest.json').read_text(encoding='utf8'))
        for url,item in manifest.items():
            from urllib.parse import urlsplit
            response=self.client.get(urlsplit(url).path)
            self.assertEqual(response.status_code,301)
            self.assertEqual(response['Location'],'/media/'+item['original'])
        self.assertEqual(self.client.get('/img/not-an-original.jpg').status_code,404)

    @override_settings(AXES_ENABLED=True,AXES_FAILURE_LIMIT=5)
    def test_admin_bruteforce_is_blocked_after_five_failures(self):
        from axes.utils import reset
        reset()
        user=get_user_model().objects.create_superuser(username='release-admin',password='correct-test-password',email='admin@example.invalid')
        path='/'+settings.ADMIN_PATH+'login/'
        for _ in range(4):
            self.assertEqual(self.client.post(path,{'username':user.username,'password':'incorrect'}).status_code,200)
        self.assertEqual(self.client.post(path,{'username':user.username,'password':'incorrect'}).status_code,429)
        self.assertEqual(self.client.post(path,{'username':user.username,'password':'correct-test-password'}).status_code,429)
        reset()
