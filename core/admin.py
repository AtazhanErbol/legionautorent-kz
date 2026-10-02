import csv
from django.contrib import admin
from django.http import HttpResponse
from django.db.models import Count
from django.contrib.contenttypes.admin import GenericStackedInline
from seo.models import Translation
from .models import SiteSettings, ContentBlock

SEO_FIELDSET = ('SEO', {'classes': ['collapse'], 'fields': ('seo_title', 'seo_description', 'seo_h1', 'canonical_url', 'robots', 'og_title', 'og_description', 'og_image')})

class TranslationInline(GenericStackedInline):
    model = Translation
    extra = 0
    max_num = 2
    fields = ['language', 'published', 'name', 'title', 'description', 'h1', 'intro', 'content', 'og_title', 'og_description']
    classes = ['collapse']
class SiteTranslationInline(TranslationInline):
    fields = ['language', 'published', 'hero_title', 'hero_text', 'partner_title', 'partner_description', 'partner_whatsapp_message', 'footer_text']

class SEOAdmin(admin.ModelAdmin):
    inlines = [TranslationInline]
    @admin.display(description='SEO: проверить')
    def seo_warning(self, obj):
        warnings = []
        if not obj.seo_title: warnings.append('Title')
        if not obj.seo_description: warnings.append('Description')
        if not obj.seo_h1: warnings.append('H1')
        if 'noindex' in obj.robots: warnings.append('noindex')
        return ', '.join(warnings) or '✓'

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    inlines = [SiteTranslationInline]
    fieldsets = [('Бренд и контакты — RU', {'fields': ('name', 'phone', 'whatsapp', 'email', 'address', 'hours', 'logo', 'favicon', 'instagram', 'map_url', 'footer_text')}), ('Первый экран — RU', {'fields': ('hero_title', 'hero_text', 'hero_image', 'hero_car', 'hero_model', 'hero_model_license')}), ('Аналитика и верификация', {'fields': ('gtm_id', 'ga4_id', 'metrika_id', 'google_verification', 'yandex_verification')}), ('Партнёры — RU', {'fields': ('show_partner_section', 'partner_title', 'partner_description', 'partner_phone', 'partner_whatsapp', 'partner_whatsapp_message')})]
    def has_add_permission(self, request): return not SiteSettings.objects.exists() and super().has_add_permission(request)
    def has_delete_permission(self, request, obj=None): return False

@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    inlines = [TranslationInline]
    list_display = ['title', 'kind', 'active', 'sort_order']
    list_editable = ['active', 'sort_order']
    list_filter = ['kind', 'active']

def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="applications.csv"'
    response.write('\ufeff')
    fields = [f for f in modeladmin.model._meta.fields]
    writer = csv.writer(response); writer.writerow([f.verbose_name for f in fields])
    for obj in queryset.select_related('city'):
        row = []
        for f in fields:
            value = str(getattr(obj, f.name) or '')
            if value.startswith(('=', '+', '-', '@', '\t', '\r')): value = "'" + value
            row.append(value)
        writer.writerow(row)
    return response
export_csv.short_description = 'Экспорт выбранных заявок (CSV)'
export_csv.allowed_permissions = ['view']

admin.site.site_header = 'Legion Auto Rent — управление'
admin.site.site_title = 'Legion CMS'
admin.site.index_title = 'Автопарк, контент и заявки'
