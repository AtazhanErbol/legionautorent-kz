"""Explicit deployment step for the approved reference montage; never imports data."""
import json
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand,CommandError
from core.models import SiteSettings

class Command(BaseCommand):
    help='Enable the approved three-frame hero video; preserve catalogue, SEO and old 3D assets.'
    def handle(self,*args,**options):
        paths={'hero_video_path':'/static/video/hero-reference.mp4','hero_poster_path':'/static/img/hero-video-poster.webp'}
        for path in [*paths.values(),'/static/img/hero-video-mobile.webp']:
            if not (settings.BASE_DIR/path.lstrip('/')).is_file():raise CommandError('Missing hero asset: '+path)
        site=SiteSettings.get_solo()
        values={**paths,'enable_hero_video':True,'enable_hero_3d':False,'hero_placeholder':False}
        for field,value in values.items():setattr(site,field,value)
        site.save();cache.clear()
        self.stdout.write(json.dumps(values))
