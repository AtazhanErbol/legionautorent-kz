import tempfile
from pathlib import Path
from types import SimpleNamespace
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory, override_settings
from django.template import Template, RequestContext
from django.urls import reverse
from django.utils.translation import override
from core.models import SiteSettings, InterfaceText, SiteSection, MenuLink
from core.cms import edit_form_copy
from core.validators import validate_hero_video
from bookings.forms import CallbackForm


class AdminWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner=get_user_model().objects.create_superuser('cms-test-owner', '', 'test-only-owner-password')
        cls.manager=get_user_model().objects.create_user('cms-test-manager', is_staff=True)
        cls.manager.user_permissions.add(Permission.objects.get(codename='view_bookingrequest'))
        cls.site=SiteSettings.objects.create()

    def test_staff_dashboard_filters_navigation_and_counts_by_permission(self):
        self.client.force_login(self.manager)
        response=self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Новые заявки')
        self.assertNotContains(response,'href="'+reverse('admin:core_sitesettings_changelist')+'"')
        self.assertEqual(self.client.get(reverse('admin:core_sitesettings_change',args=[1])).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('admin:index')).status_code,302)

    def test_owner_can_open_every_registered_model(self):
        self.client.force_login(self.owner)
        for model in admin.site._registry:
            opts=model._meta
            with self.subTest(model=opts.label):
                response=self.client.get(reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist'))
                self.assertEqual(response.status_code,200)
        self.assertContains(self.client.get(reverse('admin:core_sitesettings_change',args=[1])),'hero_video_file')

    def test_saved_interface_copy_is_localized_escaped_and_has_fallback(self):
        row,_=InterfaceText.objects.update_or_create(source='Автопарк',defaults={'section':'Каталог','ru':'<script>bad()</script>','en':'Our cars'})
        for lang,expected in [('ru','&lt;script&gt;bad()&lt;/script&gt;'),('en','Our cars')]:
            request=RequestFactory().get('/')
            request.LANGUAGE_CODE=lang
            with override(lang):
                html=Template("{% load legion_tags %}{% site_text 'Автопарк' %}").render(RequestContext(request,{}))
            self.assertEqual(html,expected)
        with override('kk'):
            request=RequestFactory().get('/kk/')
            from core.cms import text_for
            self.assertTrue(text_for(request,'Автопарк'))

    def test_cms_form_consent_is_the_same_label_used_for_storage(self):
        from bookings.forms import CONSENT_TEXT
        InterfaceText.objects.update_or_create(source=CONSENT_TEXT,defaults={'section':'Формы','ru':'Проверенный текст согласия'})
        form=CallbackForm()
        with override('ru'):edit_form_copy(RequestFactory().get('/callback/'),form)
        self.assertEqual(form.fields['consent'].label,'Проверенный текст согласия')

    def test_upload_switches_active_video_and_preserves_previous_asset(self):
        previous=self.site.hero_video_path
        with tempfile.TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            self.site.hero_video_file=SimpleUploadedFile('film.mp4', b'\0\0\0\x18ftypisom'+b'0'*32,content_type='video/mp4')
            form=SimpleNamespace(changed_data=['hero_video_file'])
            admin.site._registry[SiteSettings].save_model(RequestFactory().get('/'),self.site,form,True)
            self.site.refresh_from_db()
            self.assertEqual(self.site.hero_video_path,self.site.hero_video_file.url)
            self.assertTrue(Path(folder,self.site.hero_video_file.name).exists())
            self.assertNotEqual(previous,self.site.hero_video_path)
            self.assertTrue(Path('static',previous.removeprefix('/static/')).exists())

    def test_media_and_menu_validation(self):
        for filename,data in [('fake.mp4',b'not a movie'),('fake.html',b'\0\0\0\x18ftypisom')]:
            with self.assertRaises(ValidationError):validate_hero_video(SimpleUploadedFile(filename,data))
        with self.assertRaises(ValidationError):MenuLink(area='main',label='Bad',path='javascript:alert(1)').full_clean()
        with self.assertRaises(ValidationError):SiteSection(key='fleet',active=False).clean()

    def test_singleton_delete_not_available(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse('admin:core_sitesettings_delete',args=[1]),{'post':'yes'}).status_code,403)

    def test_settings_submit_preserves_other_content_and_saves_new_contact(self):
        from bs4 import BeautifulSoup
        self.client.force_login(self.owner)
        url=reverse('admin:core_sitesettings_change',args=[1])
        response=self.client.get(url)
        soup=BeautifulSoup(response.content,'html.parser')
        form=soup.select_one('#sitesettings_form')
        data={}
        for node in form.select('input[name],textarea[name],select[name]'):
            name=node['name'];kind=node.get('type','')
            if '__prefix__' in name or kind in ('file','submit','button') or node.has_attr('disabled'):continue
            if kind in ('checkbox','radio') and not node.has_attr('checked'):continue
            if node.name=='textarea':value=node.get_text()
            elif node.name=='select':
                selected=node.select('option[selected]') or node.select('option')[:1]
                value=[n.get('value',n.get_text()) for n in selected] if node.has_attr('multiple') else (selected[0].get('value','') if selected else '')
            else:value=node.get('value','on' if kind=='checkbox' else '')
            data[name]=value
        data.update(phone='+7 (700) 123-45-67',_save='Сохранить')
        response=self.client.post(url,data)
        self.assertEqual(response.status_code,302, response.content.decode()[:1000])
        self.site.refresh_from_db()
        self.assertEqual(self.site.phone,'+7 (700) 123-45-67')
        self.assertEqual(self.site.hero_video_path,SiteSettings._meta.get_field('hero_video_path').default)
