from django.contrib import admin
from core.admin import SEOAdmin, SEO_FIELDSET
from .models import City

@admin.register(City)
class CityAdmin(SEOAdmin):
    list_display = ['name', 'legacy_path', 'active', 'sort_order', 'seo_warning','translation_status']
    list_editable = ['active', 'sort_order']
    search_fields = ['name', 'slug', 'address']
    fieldsets = [('Город — RU', {'fields': ('name', 'name_in', 'slug', 'legacy_path', 'description','hero_text', 'body', 'active', 'sort_order')}), ('Контакты', {'fields': ('address', 'phone', 'whatsapp','hours', 'map_url', 'latitude', 'longitude')}), SEO_FIELDSET]
