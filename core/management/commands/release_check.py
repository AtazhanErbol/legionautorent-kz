from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from core.models import SiteSettings
from cars.models import Car,CarImage
from pages.models import Page
from locations.models import City
from seo.services import catalog_languages
import json

class Command(BaseCommand):
    help='Report factual release gates; --strict fails while client data/configuration remain incomplete.'
    def add_arguments(self,parser):parser.add_argument('--strict',action='store_true')
    def handle(self,*args,**options):
        gates=[]
        site=SiteSettings.get_solo()
        source=settings.BASE_DIR/'seo_audit_old_site.json'
        if source.exists():
            legacy=json.loads(source.read_text(encoding='utf8'))
            count=sum(p['status']>=400 for p in legacy['pages'])
            verification=settings.BASE_DIR/'reports/verification.json'
            result=json.loads(verification.read_text(encoding='utf8')) if verification.exists() else {}
            if count and (result.get('old_500_now_404')!=count or result.get('failures')):gates.append(f'Verify the {count} legacy error URLs against the approved 404 migration policy.')
        missing_languages=[lang for lang in ['kk','en'] if lang not in catalog_languages()]
        if missing_languages:gates.append('CMS translations remain unpublished: '+','.join(missing_languages))
        if Car.objects.filter(active=True).filter(transmission='').exists():gates.append('Vehicle characteristics and inferred categories require owner review.')
        if City.objects.filter(active=True,address='').exists():gates.append('Confirm the Pavlodar address.')
        if Page.objects.filter(slug__in=['privacy','consent'],legal_approved=False).exists():gates.append('Legal pages are drafts; owner approval is pending.')
        if site.enable_hero_video:
            path=site.hero_video_path
            asset=(settings.BASE_DIR/path.lstrip('/')) if path.startswith('/static/') else (settings.MEDIA_ROOT/path.removeprefix('/media/')) if path.startswith('/media/') else None
            if not path or asset is None or not asset.is_file():gates.append('The configured hero video is missing.')
        elif site.enable_hero_3d and not site.hero_model:gates.append('Licensed optimized GLB not provided; placeholder 3D mode remains configured.')
        if not settings.ANALYTICS_ENABLED:gates.append('Analytics disabled locally/staging; verify the existing GTM setup before production.')
        if settings.IS_STAGING:gates.append('Local/staging global noindex is active; production configuration must be verified separately.')
        report={'database_vendor':__import__('django.db',fromlist=['connection']).connection.vendor,'cars':Car.objects.public().count(),'cities':City.objects.filter(active=True).count(),'images':CarImage.objects.count(),'hero_mode':'video' if site.enable_hero_video else '3d' if site.enable_hero_3d else 'poster','release_gates':gates,'production_switched':False}
        self.stdout.write(json.dumps(report,ensure_ascii=True,indent=2))
        if options['strict'] and gates:raise CommandError('Release gates are not closed. See RELEASE_STATUS.md.')
