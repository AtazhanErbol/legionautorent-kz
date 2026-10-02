from django.contrib import admin
from core.admin import SEOAdmin, SEO_FIELDSET
from .models import City

@admin.register(City)
class CityAdmin(SEOAdmin):
    list_display = ['name', 'legacy_path', 'active', 'sort_order', 'seo_warning']
    list_editable = ['active', 'sort_order']
    search_fields = ['name', 'slug', 'address']
    fieldsets = [(None, {'fields': ('name', 'name_in', 'slug', 'legacy_path', 'description', 'body', 'active', 'sort_order')}), ('Контакты', {'fields': ('address', 'phone', 'whatsapp', 'map_url', 'latitude', 'longitude')}), SEO_FIELDSET]
