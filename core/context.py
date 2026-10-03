import os
from django.conf import settings
from django.utils.translation import gettext as _
from .models import SiteSettings
from .hero import hero_context
from .i18n import language_url, get_translation
from locations.models import City
from cars.models import CarCategory
from pages.models import Page

def site_context(request):
    site = getattr(request, 'site_settings', None) or SiteSettings.get_solo()
    if os.getenv('GTM_ID'): site.gtm_id = os.environ['GTM_ID']
    if os.getenv('WHATSAPP_NUMBER'): site.whatsapp = os.environ['WHATSAPP_NUMBER']
    hero_film = hero_context(site)
    return {'hero_film': hero_film, 'site': site, 'nav_cities': City.objects.filter(active=True).prefetch_related('translations'), 'nav_categories': CarCategory.objects.filter(active=True).prefetch_related('translations'), 'footer_pages': Page.objects.filter(active=True, show_in_footer=True).prefetch_related('translations'), 'is_staging': settings.IS_STAGING, 'analytics_enabled': settings.ANALYTICS_ENABLED, 'current_language': request.LANGUAGE_CODE, 'language_links': [{'language': language, 'label': label, 'url': language_url(getattr(request, 'base_path', request.path), language)} for language, label in [('ru', 'RU'), ('kk', 'KZ'), ('en', 'EN')]], 'partner_translated': request.LANGUAGE_CODE == 'ru' or bool(get_translation(site))}
