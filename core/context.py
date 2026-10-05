import os
from django.conf import settings
from django.utils.translation import gettext as _
from .models import SiteSettings, SiteSection, MenuLink
from .hero import hero_context
from .i18n import language_url, get_translation
from locations.models import City
from cars.models import CarCategory
from pages.models import Page

def site_context(request):
    if request.path.startswith('/' + settings.ADMIN_PATH):
        return {}
    site = getattr(request, 'site_settings', None) or SiteSettings.get_solo()
    if os.getenv('GTM_ID'): site.gtm_id = os.environ['GTM_ID']
    if os.getenv('WHATSAPP_NUMBER'): site.whatsapp = os.environ['WHATSAPP_NUMBER']
    hero_film = hero_context(site)
    sections = list(SiteSection.objects.all())
    request.home_sections = [section for section in sections if section.active] if sections else [SiteSection(key=key) for key, _ in SiteSection.KEYS]
    menu = list(MenuLink.objects.filter(active=True))
    cities = getattr(request, 'nav_cities', None)
    if cities is None: cities = list(City.objects.filter(active=True).prefetch_related('translations'))
    selected = getattr(request, 'selected_city', None)
    request.selected_city = selected or next((city for city in cities if city.legacy_path == request.base_path), None)
    request.main_menu = [item for item in menu if item.area == 'main']
    request.mobile_menu = [item for item in menu if item.area == 'mobile']
    return {'hero_film': hero_film, 'site': site, 'nav_cities': cities, 'nav_categories': CarCategory.objects.filter(active=True).prefetch_related('translations'), 'footer_pages': Page.objects.filter(active=True, show_in_footer=True).prefetch_related('translations'), 'is_staging': settings.IS_STAGING, 'analytics_enabled': settings.ANALYTICS_ENABLED, 'current_language': request.LANGUAGE_CODE, 'language_links': [{'language': language, 'label': label, 'url': language_url(getattr(request, 'base_path', request.path), language)} for language, label in [('ru', 'RU'), ('kk', 'KZ'), ('en', 'EN')]], 'partner_translated': request.LANGUAGE_CODE == 'ru' or bool(get_translation(site))}
