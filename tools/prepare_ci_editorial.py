"""Replay the already approved SEO manifest in an isolated CI fixture only.

Production deployments restore the owner's database instead. This script does
not change the raw importer, snapshots, URLs or the approval manifest.
"""
import json
import os
import sys
from pathlib import Path

if os.environ.get('LEGION_CI_FIXTURE') != '1':
    raise SystemExit('Only for an explicitly marked disposable CI database.')
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legion.config.development')
import django
django.setup()
from django.conf import settings
from django.db import transaction
from cars.models import Car
from locations.models import City
from seo.editorial import normalized

if settings.ENVIRONMENT != 'development':
    raise SystemExit('Production databases are not supported by this fixture.')
manifest = json.loads((root / 'migration/seo_editorial_overrides.json').read_text(encoding='utf8'))
objects = {obj.legacy_path: obj for model in (Car, City) for obj in model.objects.all()}
mapping = {'title': 'seo_title', 'description': 'seo_description', 'h1': 'seo_h1', 'seo_text': 'body'}
updated = 0
with transaction.atomic():
    for path, fields in manifest['pages'].items():
        obj = objects[path]
        dirty = []
        for field, item in fields.items():
            attr = mapping.get(field)
            if not attr:
                continue
            current = getattr(obj, attr)
            if normalized(current) == normalized(item['after']):
                continue
            if normalized(current) != normalized(item['before']):
                raise RuntimeError(f'Unexpected fixture value: {path} {field}')
            setattr(obj, attr, item['after'])
            dirty.append(attr)
        if dirty:
            obj.save(update_fields=dirty + ['updated_at'])
            updated += 1
print(f'Approved editorial fixture restored for {updated} pages.')
