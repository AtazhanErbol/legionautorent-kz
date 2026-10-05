import csv
from django.contrib import admin
from django.http import HttpResponse
from django.db.models import Count
from django.contrib.contenttypes.admin import GenericStackedInline
from seo.models import Translation
from .models import SiteSettings, ContentBlock, InterfaceText, SiteSection, MenuLink
from .admin_forms import FriendlyFieldsMixin, SiteSettingsForm
from django.utils.html import format_html
from .hero import asset_url

SEO_FIELDSET = ('SEO', {'classes': ['collapse'], 'fields': ('seo_title', 'seo_description', 'seo_h1', 'canonical_url', 'robots', 'og_title', 'og_description', 'og_image','legacy_meta')})

class TranslationInline(FriendlyFieldsMixin, GenericStackedInline):
    model = Translation
    extra = 2
    max_num = 2
    fields = ['language', 'published', 'name', 'title', 'description', 'h1', 'intro', 'content','hero_text', 'address','hours','fuel','color','caption','og_title', 'og_description']
    classes = ['translation-inline']
    def get_fields(self, request, obj=None):
        common = ['language', 'published']
        seo = ['title', 'description', 'h1', 'content', 'og_title', 'og_description']
        fields = {
            'car': ['name', *seo, 'fuel', 'color'],
            'city': ['name', *seo, 'hero_text', 'address', 'hours'],
            'page': ['name', *seo, 'intro'],
            'carcategory': ['name', *seo],
            'faq': ['title', 'content'], 'contentblock': ['title', 'content'],
            'carimage': ['name', 'caption'], 'carprice': ['title'],
            'carspecification': ['name', 'content'],
        }.get(self.parent_model._meta.model_name)
        return common + fields if fields else super().get_fields(request, obj)
    class Media:
        js=['admin/editor.js']
        css={'all':['admin/editor.css']}
class SiteTranslationInline(TranslationInline):
    fields = ['language', 'published', 'hero_title', 'hero_price_caption', 'hero_steps_caption', 'hero_text', 'address','hours','whatsapp_message','partner_title', 'partner_description', 'partner_whatsapp_message', 'footer_text']

class SEOAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    inlines = [TranslationInline]
    def get_queryset(self,request):return super().get_queryset(request).prefetch_related('translations')
    @admin.display(description='Переводы')
    def translation_status(self,obj):
        complete={t.language for t in obj.translations.all() if t.published}
        return ' · '.join(f'{lang.upper()}: '+('✓' if lang in complete else 'черновик / нет') for lang in ('kk','en'))
    @admin.display(description='SEO: проверить')
    def seo_warning(self, obj):
        warnings = []
        if not obj.seo_title: warnings.append('Title')
        if not obj.seo_description: warnings.append('Description')
        if not obj.seo_h1: warnings.append('H1')
        if 'noindex' in obj.robots: warnings.append('noindex')
        return ', '.join(warnings) or '✓'

@admin.register(SiteSettings)
class SiteSettingsAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    form = SiteSettingsForm
    readonly_fields = ['hero_preview']
    inlines = [SiteTranslationInline]
    fieldsets = [('Бренд и контакты — RU', {'fields': ('name', 'phone', 'whatsapp','whatsapp_message', 'email', 'address', 'hours', 'logo', 'favicon', 'instagram', 'map_url', 'footer_text')}), ('Первый экран — RU', {'fields': ('hero_title', 'hero_price_caption', 'hero_steps_caption', 'hero_text', 'hero_image', 'hero_car', 'enable_hero_video', 'hero_video_path', 'hero_mobile_video_path', 'hero_poster_path', 'hero_mobile_poster_path', 'hero_ending_path')}), ('SEO, аналитика и верификация', {'fields': ('default_seo_title','default_seo_description','robots_text','gtm_id', 'ga4_id', 'metrika_id', 'google_verification', 'yandex_verification','notifications_enabled')}), ('Партнёры — RU', {'fields': ('show_partner_section', 'partner_title', 'partner_description', 'partner_phone', 'partner_whatsapp', 'partner_whatsapp_message')})]
    def has_add_permission(self, request): return not SiteSettings.objects.exists() and super().has_add_permission(request)
    def has_delete_permission(self, request, obj=None): return False

    @admin.display(description='Текущий первый экран')
    def hero_preview(self, obj):
        return format_html('<div class="cms-media-preview"><img src="{}" width="480" height="270" alt="Текущий постер"><div><a href="{}" target="_blank" rel="noopener">Открыть видео ↗</a><p>Публикуется только после сохранения. H1 редактируется в разделе «Города → SEO».</p></div></div>', asset_url(obj.hero_poster_path), asset_url(obj.hero_video_path))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        paths = []
        for upload, path in [('hero_video_file', 'hero_video_path'), ('hero_mobile_video_file', 'hero_mobile_video_path'), ('hero_image', 'hero_poster_path'), ('hero_mobile_image', 'hero_mobile_poster_path'), ('hero_ending_image', 'hero_ending_path')]:
            if upload in form.changed_data and getattr(obj, upload):
                setattr(obj, path, getattr(obj, upload).url)
                paths.append(path)
        if paths:
            obj.save(update_fields=paths)

    def get_fieldsets(self, request, obj=None):
        return [
            ('Бренд', {'fields': ('name', 'logo', 'favicon', 'footer_text')}),
            ('Контакты', {'fields': ('phone', 'whatsapp', 'whatsapp_message', 'email', 'address', 'hours', 'instagram', 'map_url')}),
            ('Видео и изображения', {'description': 'Загрузите файлы и сохраните. Пустое поле загрузки оставляет текущий файл. На компьютере прокрутка управляет видео. На телефоне анимация запускается после первого касания или прокрутки, без плеера. При экономии трафика и ограничении анимации показывается отдельный кадр.', 'fields': ('hero_preview', 'enable_hero_video', 'hero_video_file', 'hero_video_fps', 'hero_mobile_video_file', 'hero_image', 'hero_mobile_image', 'hero_ending_image')}),
            ('Подписи первого экрана — RU', {'fields': ('hero_title', 'hero_price_caption', 'hero_steps_caption', 'hero_text', 'hero_car')}),
            ('Партнёрский блок — RU', {'fields': ('show_partner_section', 'partner_title', 'partner_description', 'partner_phone', 'partner_whatsapp', 'partner_whatsapp_message')}),
            ('Активные пути медиа', {'classes': ['collapse'], 'description': 'Заполняются при загрузке. Можно выбрать существующий локальный файл; новые файлы удобнее загрузить выше.', 'fields': ('hero_video_path', 'hero_mobile_video_path', 'hero_poster_path', 'hero_mobile_poster_path', 'hero_ending_path')}),
            ('Аналитика и подтверждение домена', {'classes': ['collapse'], 'description': 'Сайт подключает только GTM. GA4 и Метрика должны быть настроены внутри контейнера; их ID здесь справочные. Переменные GTM_ID и WHATSAPP_NUMBER сервера, если заданы, имеют приоритет.', 'fields': ('gtm_id', 'ga4_id', 'metrika_id', 'google_verification', 'yandex_verification', 'notifications_enabled')}),
            ('Общие SEO-настройки', {'classes': ['collapse'], 'fields': ('default_seo_title', 'default_seo_description', 'robots_text')}),
        ]

@admin.register(ContentBlock)
class ContentBlockAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    inlines = [TranslationInline]
    list_display = ['title', 'kind', 'active', 'sort_order']
    list_editable = ['active', 'sort_order']
    list_filter = ['kind', 'active']
    search_fields = ['title', 'text']


@admin.register(InterfaceText)
class InterfaceTextAdmin(admin.ModelAdmin):
    list_display = ['source', 'section', 'ru', 'kk', 'en']
    list_filter = ['section']
    search_fields = ['source', 'ru', 'kk', 'en']
    readonly_fields = ['source', 'section']
    fields = ['source', 'section', 'ru', 'kk', 'en']
    list_per_page = 30
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(SiteSection)
class SiteSectionAdmin(admin.ModelAdmin):
    list_display = ['key', 'active', 'sort_order']
    list_editable = ['active', 'sort_order']
    readonly_fields = ['key']
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(MenuLink)
class MenuLinkAdmin(admin.ModelAdmin):
    list_display = ['label', 'area', 'path', 'active', 'sort_order']
    list_filter = ['area', 'active']
    list_editable = ['active', 'sort_order']
    search_fields = ['label', 'path']

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

admin.site.site_header = 'LEGIONAUTORENT — управление'
admin.site.site_title = 'LEGIONAUTORENT CMS'
admin.site.index_title = 'Автопарк, контент и заявки'
