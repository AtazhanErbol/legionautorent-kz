"""Explicit deployment step for the approved reference montage; never imports data."""
import json
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand,CommandError
from core.models import SiteSettings
from core.hero import ASSETS

class Command(BaseCommand):
    help='Enable the owner-approved Mercedes film; preserve catalogue, SEO and previous assets.'
    def handle(self,*args,**options):
        paths={'hero_video_path':ASSETS['video'],'hero_poster_path':ASSETS['poster'],
               'hero_mobile_poster_path':ASSETS['mobile'],'hero_ending_path':ASSETS['ending']}
        for path in paths.values():
            if not (settings.BASE_DIR/path.lstrip('/')).is_file():raise CommandError('Missing hero asset: '+path)
        site=SiteSettings.get_solo()
        values={**paths,'enable_hero_video':True,'enable_hero_3d':False,'hero_placeholder':False}
        for field,value in values.items():setattr(site,field,value)
        site.save();cache.clear()
        self.stdout.write(json.dumps(values))
