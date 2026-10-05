from core.admin_forms import FriendlyFieldsMixin
from django.contrib import admin
from core.admin import SEOAdmin, SEO_FIELDSET
from .models import City

@admin.register(City)
class CityAdmin(SEOAdmin):
    list_display = ['name', 'legacy_path', 'active', 'sort_order', 'seo_warning','translation_status']
    list_editable = ['active', 'sort_order']
    search_fields = ['name', 'slug', 'address']
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'map_url':
            kwargs['help_text'] = 'Ссылка src из iframe Яндекс Карт. Если поле пустое или повторяет общую карту Астаны, карта ищет адрес этого города. Для точной метки вставьте собственную ссылку виджета.'
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    fieldsets = [('Город — RU', {'fields': ('name', 'name_in', 'slug', 'legacy_path', 'description','hero_text', 'body', 'active', 'sort_order')}), ('Контакты', {'fields': ('address', 'phone', 'whatsapp','hours', 'map_url', 'latitude', 'longitude')}), SEO_FIELDSET]
