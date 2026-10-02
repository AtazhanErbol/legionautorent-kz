import json
import re
from urllib.parse import quote
import nh3
from django import template
from django.utils.safestring import mark_safe
from core.i18n import localized, language_url

register = template.Library()
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
