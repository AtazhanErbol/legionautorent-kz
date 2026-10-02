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
            if count:gates.append(f'{count} legacy URLs require restoration or owner-reviewed individual redirects.')
        missing_languages=[lang for lang in ['kk','en'] if lang not in catalog_languages()]
        if missing_languages:gates.append('CMS translations remain unpublished: '+','.join(missing_languages))
        if Car.objects.filter(active=True).filter(transmission='').exists():gates.append('Vehicle characteristics and inferred categories require owner review.')
        if City.objects.filter(active=True,address='').exists():gates.append('Confirm the Pavlodar address.')
        if Page.objects.filter(slug__in=['privacy','consent'],legal_approved=False).exists():gates.append('Legal pages are drafts; owner approval is pending.')
        if not site.hero_model:gates.append('Licensed optimized GLB not provided; hero photo fallback active.')
        if not settings.ANALYTICS_ENABLED:gates.append('Analytics disabled locally/staging; verify the existing GTM setup before production.')
        if settings.IS_STAGING:gates.append('Local/staging global noindex is active; production configuration must be verified separately.')
        report={'database_vendor':__import__('django.db',fromlist=['connection']).connection.vendor,'cars':Car.objects.public().count(),'cities':City.objects.filter(active=True).count(),'images':CarImage.objects.count(),'release_gates':gates,'production_switched':False}
        self.stdout.write(json.dumps(report,ensure_ascii=True,indent=2))
        if options['strict'] and gates:raise CommandError('Release gates are not closed. See RELEASE_STATUS.md.')
