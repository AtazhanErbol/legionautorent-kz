from django.core.cache import cache
from django.db.models.signals import post_save, post_delete, m2m_changed
from cars.models import Car,CarCategory
from locations.models import City
from seo.models import Translation
from core.models import SiteSettings,ContentBlock,InterfaceText,SiteSection,MenuLink
from pages.models import Page,FAQ
from cars.models import CarImage,CarPrice,CarSpecification,CarDiscount
import uuid

def invalidate_catalog(sender,**kwargs):
    from django.db import connection,transaction
    if 'legion_cache' in connection.introspection.table_names():
        def expire():
            cache.delete('catalog_languages')
            cache.set('page_revision',uuid.uuid4().hex,None)
        transaction.on_commit(expire)

for model in [Car,CarCategory,City,Translation,SiteSettings,ContentBlock,InterfaceText,SiteSection,MenuLink,Page,FAQ,CarImage,CarPrice,CarSpecification,CarDiscount]:
    post_save.connect(invalidate_catalog,sender=model,dispatch_uid=f'catalog_save_{model._meta.label}')
    post_delete.connect(invalidate_catalog,sender=model,dispatch_uid=f'catalog_delete_{model._meta.label}')
m2m_changed.connect(invalidate_catalog,sender=Car.cities.through,dispatch_uid='catalog_cities')
