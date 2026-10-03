import json
import re
from urllib.parse import quote
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
@register.filter
def tr(obj, field): return localized(obj, field)
@register.filter
def money(value): return f'{int(value):,}'.replace(',', ' ') if value is not None else ''
@register.filter
def local_url(value): return language_url(str(value))
@register.filter
def richtext(value):
    return mark_safe(nh3.clean(value or '', tags={'p','h2','h3','h4','strong','em','ul','ol','li','a','br','blockquote'}, attributes={'a': {'href', 'title'}}, url_schemes={'http', 'https', 'mailto', 'tel'}, link_rel='noopener noreferrer'))
@register.filter
def phone_link(value): return '+' + re.sub(r'\D', '', value or '')
@register.simple_tag
def wa_url(number, message): return f'https://wa.me/{re.sub(r"[^0-9]", "", number or "")}?text={quote(message)}'
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
    'close':'<path d="m6 6 12 12M18 6 6 18"/>',
    'arrow':'<path d="M5 19 19 5M5 5h14v14"/>',
    'phone':'<path d="M5 3h4l2 5-3 2c2 3 3 4 6 6l2-3 5 2v4a2 2 0 0 1-2 2C10 21 3 14 3 5a2 2 0 0 1 2-2Z"/>',
    'whatsapp':'<path d="M20 11.6a8.2 8.2 0 0 1-12.2 7.1L3 20l1.3-4.6A8.2 8.2 0 1 1 20 11.6Z"/><path d="m8 7 1 3-1 1c1 2 2 3 4 4l1-1 3 1c0 2-2 2-3 2-4-1-7-4-7-7 0-1 1-3 2-3Z"/>',
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
