"""Exact owner-requested SEO exceptions; all other migration values stay protected."""
import json
import re
from pathlib import Path
from django.conf import settings


def normalized(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def editorial_expected(path, field, original):
    manifest=Path(settings.BASE_DIR)/'migration/seo_editorial_overrides.json'
    if not manifest.exists():return original
    item=json.loads(manifest.read_text(encoding='utf8')).get('pages',{}).get(path,{}).get(field)
    if item and normalized(item['before'])==normalized(original):return item['after']
    return original
