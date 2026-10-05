import json
import re
from urllib.parse import quote
from urllib.parse import urlsplit, parse_qsl, urlencode
from html import unescape
import nh3
from django import template
from django.utils.safestring import mark_safe
from core.i18n import localized, language_url
from django.conf import settings
from pathlib import Path
from django.utils.translation import gettext as _

register = template.Library()
@register.simple_tag
def asset(entry):
    manifest=Path(settings.BASE_DIR)/'static/build/.vite/manifest.json'
    if manifest.exists():
        data=json.loads(manifest.read_text(encoding='utf8'))
        return settings.STATIC_URL+'build/'+data[entry]['file']
    return settings.STATIC_URL+'build/missing-build.js'
@register.simple_tag
def asset_css(entry):
    manifest=Path(settings.BASE_DIR)/'static/build/.vite/manifest.json'
    if manifest.exists():
        data=json.loads(manifest.read_text(encoding='utf8'))
        return [settings.STATIC_URL+'build/'+item for item in data[entry].get('css',[])]
    return []
@register.simple_tag
def critical_css(entry):
    """The shared stylesheet avoids an extra blocking mobile round trip."""
    folder=Path(settings.BASE_DIR)/'static/build'
    manifest=folder/'.vite/manifest.json'
    if not manifest.exists():return ''
    data=json.loads(manifest.read_text(encoding='utf8'))
    content='\n'.join((folder/file).read_text(encoding='utf8') for file in data[entry].get('css',[]))
    return mark_safe(content.replace('</style','<\\/style'))

@register.simple_tag(takes_context=True)
def site_text(context, source):
    from core.cms import text_for
    return text_for(context['request'], source)
@register.simple_tag(takes_context=True)
def menu_url(context, path):
    city = getattr(context['request'], 'selected_city', None)
    parts = urlsplit(path)
    if city and (parts.path == '/cars/' or parts.path.startswith('/cars/category/')):
        query = dict(parse_qsl(parts.query))
        query.setdefault('city', city.slug)
        path = parts._replace(query=urlencode(query)).geturl()
    return language_url(path)
@register.filter
def tr(obj, field): return localized(obj, field)
@register.filter
def money(value): return f'{int(value):,}'.replace(',', ' ') if value is not None else ''
@register.filter
def local_url(value): return language_url(str(value))
@register.filter
def richtext(value):
    clean = nh3.clean(value or '', tags={'p','h2','h3','h4','strong','em','ul','ol','li','a','br','blockquote'}, attributes={'a': {'href', 'title'}}, url_schemes={'http', 'https', 'mailto', 'tel'}, link_rel='noopener noreferrer')
    def external_chat(match):
        tag = match.group(0)
        href = re.search(r'href="([^"]*)"', tag)
        try: host = urlsplit(unescape(href[1])).hostname if href else None
        except ValueError: host = None
        if host in ('wa.me', 'api.whatsapp.com', 'web.whatsapp.com', 'www.whatsapp.com'):
            return tag[:-1] + ' target="_blank">'
        return tag
    return mark_safe(re.sub(r'<a\b[^>]*>', external_chat, clean))
@register.filter
def phone_link(value): return '+' + re.sub(r'\D', '', value or '')
@register.simple_tag
def wa_url(number, message): return f'https://wa.me/{re.sub(r"[^0-9]", "", number or "")}?text={quote(message)}'
@register.simple_tag
def map_link(city, site):
    address = (city.address or city.name) if city else site.address
    return 'https://yandex.ru/maps/?text=' + quote(address) if address else site.map_url
@register.simple_tag
def map_embed(city, site):
    # The legacy import copied Astana's constructor URL to every city. Keep a
    # city's own configured widget, but never show Astana for another address.
    if city and city.map_url and (city.map_url != site.map_url or city.legacy_path == '/'):
        return city.map_url
    if not city or city.legacy_path == '/':
        if site.map_url:
            return site.map_url
    address = (city.address or city.name) if city else site.address
    address = re.sub(r'\s*,?\s*(?:офис|ВП-|каб\.)\s*.*$', '', address, flags=re.IGNORECASE)
    return 'https://yandex.ru/map-widget/v1/?' + urlencode({'mode':'search', 'text':address, 'z':16 if city and city.address else 12}) if address else ''
@register.simple_tag
def car_wa_url(number, car, city=None):
    message=_('Здравствуйте! Интересует аренда %(car)s.') % {'car':localized(car,'name')}
    if city: message+=' '+localized(city,'name')
    return wa_url(number,message)
@register.simple_tag
def car_discount(car):
    return max((item.percent for item in car.discounts.all()),default=0)

# Trusted, small inline icons avoid an external font or icon library.
ICONS={
    'chevron':'<path d="m6 9 6 6 6-6"/>',
    'close':'<path d="m6 6 12 12M18 6 6 18"/>',
    'arrow':'<path d="M5 19 19 5M5 5h14v14"/>',
    'phone':'<path d="M5 3h4l2 5-3 2c2 3 3 4 6 6l2-3 5 2v4a2 2 0 0 1-2 2C10 21 3 14 3 5a2 2 0 0 1 2-2Z"/>',
    'whatsapp':'<path d="M20.52 3.48A11.86 11.86 0 0 0 12.06 0C5.5 0 .16 5.34.16 11.9c0 2.1.55 4.15 1.59 5.95L.06 24l6.3-1.65a11.87 11.87 0 0 0 5.69 1.45h.01c6.56 0 11.9-5.34 11.9-11.9a11.83 11.83 0 0 0-3.44-8.42ZM12.06 21.8a9.87 9.87 0 0 1-5.03-1.38l-.36-.21-3.74.98 1-3.64-.24-.37a9.85 9.85 0 0 1-1.52-5.28c0-5.45 4.44-9.89 9.9-9.89a9.82 9.82 0 0 1 7 2.9 9.83 9.83 0 0 1 2.89 7c0 5.45-4.44 9.89-9.9 9.89Zm5.43-7.41c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.25-.46-2.39-1.47-.88-.78-1.48-1.74-1.65-2.04-.17-.3-.02-.46.13-.61.14-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.61-.92-2.2-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.21 3.08c.15.2 2.1 3.2 5.08 4.49.71.31 1.27.49 1.7.63.72.23 1.37.2 1.88.12.58-.09 1.76-.72 2.01-1.41.25-.7.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35Z" fill="currentColor" stroke="none"/>',
    'pin':'<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    'calendar':'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 11h18m-13 5h2m4 0h2"/>',
    'car':'<path d="m4 10 2-6h12l2 6M3 16v4m18-4v4M3 10h18v7H3Zm2 3h3m8 0h3"/>',
    'key':'<circle cx="8" cy="8" r="5"/><path d="m12 12 9 9m-5-5 3-3m-1 5 3-3"/>',
    'shield':'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Zm-4 9 3 3 5-6"/>',
    'clock':'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    'check':'<path d="m5 12 4 4L19 6"/>',
    'gear':'<path d="M6 4v16m6-16v8m6-8v8M6 12h12"/><circle cx="6" cy="4" r="1"/><circle cx="12" cy="4" r="1"/><circle cx="18" cy="4" r="1"/>',
    'drive':'<circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h8M8 18h8M12 6v12"/>',
    'seat':'<path d="M7 4v10h11l2 6H6L4 4Zm3 10 1-5h5"/>',
}
@register.simple_tag
def icon(name):
    return mark_safe('<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+'<use href="#legion-icon-'+(name if name in ICONS else 'arrow')+'"/>'+'</svg>')
@register.simple_tag
def icon_sprite():
    symbols = ''.join('<symbol id="legion-icon-'+name+'" viewBox="0 0 24 24">'+paths+'</symbol>' for name, paths in ICONS.items())
    return mark_safe('<svg class="icon-definitions" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">'+symbols+'</svg>')
@register.filter
def json_ld(value):
    return mark_safe(json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))
