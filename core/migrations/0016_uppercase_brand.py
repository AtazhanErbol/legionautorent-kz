"""The owner confirmed uppercase LEGIONAUTORENT after the spelling migration."""
from importlib import import_module
from django.db import migrations, models


def forwards(apps, schema_editor):
    original=import_module('core.migrations.0015_normalize_brand_content')
    alias=schema_editor.connection.alias
    for app, name in original.MODELS:
        model=apps.get_model(app,name)
        fields=[f.name for f in model._meta.fields if f.name in original.FIELDS and isinstance(f,(models.CharField,models.TextField)) and not isinstance(f,models.URLField)]
        for obj in model.objects.using(alias).all().iterator():
            changes={}
            for field in fields:
                before=getattr(obj,field)
                if not isinstance(before,str):continue
                after=original.PATTERN.sub('LEGIONAUTORENT',before)
                if after!=before:changes[field]=after
            if changes:model.objects.using(alias).filter(pk=obj.pk).update(**changes)


class Migration(migrations.Migration):
    dependencies=[('core','0015_normalize_brand_content')]
    operations=[migrations.RunPython(forwards,migrations.RunPython.noop)]
