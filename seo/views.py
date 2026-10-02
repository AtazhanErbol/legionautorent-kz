from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from locations.models import City
from cars.models import Car, CarCategory
from pages.models import Page
from core.i18n import language_url
from .services import languages_for, catalog_languages

@require_GET
def robots(request):
    text = 'User-agent: *\nDisallow: /\n' if settings.IS_STAGING else f'User-agent: *\nDisallow: /admin/\nDisallow: /booking/\nDisallow: /kz/booking/\nDisallow: /en/booking/\nDisallow: /request-success/\nDisallow: /kz/request-success/\nDisallow: /en/request-success/\nSitemap: {settings.SITE_URL}/sitemap.xml\n'
    return HttpResponse(text, content_type='text/plain; charset=utf-8')

@require_GET
def sitemap(request):
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    xhtml = 'http://www.w3.org/1999/xhtml'
    register_namespace('', ns); register_namespace('xhtml', xhtml)
    root = Element(f'{{{ns}}}urlset')
    groups = [City.objects.filter(active=True, robots='index,follow').prefetch_related('translations'), Car.objects.public().filter(robots='index,follow').prefetch_related('translations'), CarCategory.objects.filter(active=True, robots='index,follow').prefetch_related('translations'), Page.objects.filter(active=True, robots='index,follow').prefetch_related('translations')]
    entries = [(obj.get_absolute_url(), languages_for(obj), obj.updated_at) for group in groups for obj in group]
    entries.append(('/cars/', catalog_languages(), None))
    for path, languages, modified in entries:
        for lang in languages:
            node = SubElement(root, f'{{{ns}}}url')
            SubElement(node, f'{{{ns}}}loc').text = settings.SITE_URL + language_url(path, lang)
            if modified: SubElement(node, f'{{{ns}}}lastmod').text = modified.isoformat()
            for alt in languages:
                SubElement(node, f'{{{xhtml}}}link', {'rel': 'alternate', 'hreflang': alt, 'href': settings.SITE_URL + language_url(path, alt)})
            SubElement(node, f'{{{xhtml}}}link', {'rel': 'alternate', 'hreflang': 'x-default', 'href': settings.SITE_URL + path})
    return HttpResponse(tostring(root, encoding='utf-8', xml_declaration=True), content_type='application/xml')
