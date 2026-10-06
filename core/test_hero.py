from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from core.hero import ASSETS, hero_context
from core.models import SiteSettings
from core.admin import SiteSettingsAdmin
from django.contrib import admin


class HeroSettingsTests(TestCase):
    def test_approved_assets_are_available_in_production(self):
        with override_settings(ENVIRONMENT='production', IS_STAGING=False):
            hero = hero_context(SiteSettings())
        self.assertIn('hero-60fps', hero['video'])
        self.assertIn('hero-poster-', hero['poster'])
        self.assertGreater(hero['sequence']['count'], 500)
        self.assertEqual(hero['sequence']['mobile']['packs'][0].split('/')[-1][:9], 'mobile-00')

    def test_disabling_video_preserves_complete_poster(self):
        hero = hero_context(SiteSettings(enable_hero_video=False))
        self.assertEqual(hero['video'], '')
        self.assertEqual(hero['sequence'], {})
        self.assertTrue(hero['poster'])

    def test_local_custom_media_is_used(self):
        hero = hero_context(SiteSettings(hero_video_path='/media/site/custom.mp4',
             hero_poster_path='/media/site/custom.webp',hero_mobile_poster_path=''))
        self.assertEqual(hero['video'], '/media/site/custom.mp4')
        self.assertEqual(hero['mobile'], '/media/site/custom.webp')
        self.assertEqual(hero['sequence'], {})

    def test_new_asset_paths_reject_remote_or_traversal(self):
        for name in ('hero_mobile_poster_path','hero_ending_path'):
            for value in ('https://other.invalid/file.webp','/static/../file.webp'):
                with self.assertRaises(ValidationError):
                    SiteSettings(**{name:value}).full_clean()

    def test_retired_3d_controls_not_exposed_in_admin(self):
        fields = str(SiteSettingsAdmin(SiteSettings,admin.site).fieldsets)
        for field in ('enable_hero_3d','hero_model','hero_names','hero_placeholder'):
            self.assertNotIn(field,fields)
        self.assertIn('hero_title',fields)
        self.assertNotIn('seo_h1',fields)
