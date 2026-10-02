import json
import re
from urllib.parse import quote
import nh3
from django import template
from django.utils.safestring import mark_safe
from core.i18n import localized, language_url
from django.conf import settings
from pathlib import Path

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
    """The complete 6 KB gzip stylesheet avoids an extra blocking mobile round trip."""
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
@register.filter
def json_ld(value):
    return mark_safe(json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))
