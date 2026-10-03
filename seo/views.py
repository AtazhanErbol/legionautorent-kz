from xml.etree.ElementTree import Element,SubElement,tostring,register_namespace
from django.conf import settings
from django.http import HttpResponse,Http404
from django.views.decorators.http import require_safe
from locations.models import City
from cars.models import Car,CarCategory
from pages.models import Page
from core.models import SiteSettings
from core.i18n import language_url
from .services import languages_for,catalog_languages,faq_languages

NS='http://www.sitemaps.org/schemas/sitemap/0.9';XHTML='http://www.w3.org/1999/xhtml'
register_namespace('',NS);register_namespace('xhtml',XHTML)
SECTIONS=('cities','cars','categories','pages')

@require_safe
def robots(request):
    if settings.IS_STAGING:text='User-agent: *\nDisallow: /\n'
    else:
        site=SiteSettings.get_solo();url=settings.SITE_URL+'/sitemap.xml'
        text=site.robots_text.replace('{sitemap_url}',url) if site.robots_text else f'User-agent: *\nDisallow: /{settings.ADMIN_PATH}\nDisallow: /booking/\nDisallow: /callback/\nDisallow: /request-success/\nDisallow: /kk/booking/\nDisallow: /en/booking/\n'
        if 'Sitemap:' not in text:text+='\nSitemap: '+url+'\n'
    return HttpResponse(text,content_type='text/plain; charset=utf-8')

@require_safe
def sitemap(request,section=None):
    if section is None:
        root=Element(f'{{{NS}}}sitemapindex')
        latest=max([d for d in [Car.objects.order_by('-updated_at').values_list('updated_at',flat=True).first(),City.objects.order_by('-updated_at').values_list('updated_at',flat=True).first()] if d],default=None)
        for name in SECTIONS:
            item=SubElement(root,f'{{{NS}}}sitemap');SubElement(item,f'{{{NS}}}loc').text=f'{settings.SITE_URL}/sitemap-{name}.xml'
            if latest:SubElement(item,f'{{{NS}}}lastmod').text=latest.isoformat()
    else:
        if section not in SECTIONS:raise Http404()
        groups={'cities':City.objects.filter(active=True,robots='index,follow'), 'cars':Car.objects.public().filter(robots='index,follow'), 'categories':CarCategory.objects.filter(active=True,robots='index,follow'), 'pages':Page.objects.filter(active=True,robots='index,follow')}
        entries=[(obj.get_absolute_url(),languages_for(obj),obj.updated_at) for obj in groups[section].prefetch_related('translations')]
        if section=='pages':entries.extend([('/cars/',catalog_languages(),None),('/faq/',faq_languages(),None)])
        root=Element(f'{{{NS}}}urlset')
        for path,languages,modified in entries:
            for lang in languages:
                item=SubElement(root,f'{{{NS}}}url');SubElement(item,f'{{{NS}}}loc').text=settings.SITE_URL+language_url(path,lang)
                if modified:SubElement(item,f'{{{NS}}}lastmod').text=modified.isoformat()
                for alternate in languages:SubElement(item,f'{{{XHTML}}}link',{'rel':'alternate','hreflang':alternate,'href':settings.SITE_URL+language_url(path,alternate)})
                SubElement(item,f'{{{XHTML}}}link',{'rel':'alternate','hreflang':'x-default','href':settings.SITE_URL+path})
    return HttpResponse(tostring(root,encoding='utf8',xml_declaration=True),content_type='application/xml')
