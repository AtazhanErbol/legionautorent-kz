from django.core.cache import cache
from django.db.models.signals import post_save, post_delete, m2m_changed
from cars.models import Car,CarCategory
from locations.models import City
from seo.models import Translation

def invalidate_catalog(sender,**kwargs):
    from django.db import connection,transaction
    if 'legion_cache' in connection.introspection.table_names():
        transaction.on_commit(lambda:cache.delete('catalog_languages'))

for model in [Car,CarCategory,City,Translation]:
    post_save.connect(invalidate_catalog,sender=model,dispatch_uid=f'catalog_save_{model._meta.label}')
    post_delete.connect(invalidate_catalog,sender=model,dispatch_uid=f'catalog_delete_{model._meta.label}')
m2m_changed.connect(invalidate_catalog,sender=Car.cities.through,dispatch_uid='catalog_cities')
