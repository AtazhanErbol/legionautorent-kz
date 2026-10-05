from core.admin_forms import FriendlyFieldsMixin
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from core.admin import SEOAdmin, SEO_FIELDSET, TranslationInline
from .models import Car, CarImage, CarPrice, CarDiscount, CarBrand, CarCategory, CarFeature
from .models import CarSpecification
from django.utils.html import format_html

class ImageFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):return
        if sum(bool(f.cleaned_data.get('is_main')) for f in self.forms if f.cleaned_data and not f.cleaned_data.get('DELETE'))>1:
            raise ValidationError('Выберите только одно главное изображение.')
class PriceFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):return
        ranges=sorted((f.cleaned_data['min_days'],f.cleaned_data.get('max_days')) for f in self.forms if f.cleaned_data and not f.cleaned_data.get('DELETE'))
        for i in range(1,len(ranges)):
            if ranges[i-1][1] is None or ranges[i][0]<=ranges[i-1][1]:raise ValidationError('Диапазоны тарифов не должны пересекаться.')

class ImageInline(FriendlyFieldsMixin, admin.TabularInline):
    verbose_name_plural = 'Фотографии'
    model = CarImage
    formset=ImageFormSet
    extra = 0
    fields = ['preview','original','alt','caption','is_main','sort_order','legacy_url']
    readonly_fields = ['legacy_url','preview']
    classes=['sortable-inline']
    @admin.display(description='Фото')
    def preview(self,obj):return format_html('<img class="admin-photo" src="{}" width="80" height="56" alt="">',obj.card_url) if obj.pk and obj.original else '—'
class PriceInline(FriendlyFieldsMixin, admin.TabularInline):
    verbose_name_plural = 'Тарифы по сроку аренды'
    model = CarPrice
    formset=PriceFormSet
    extra = 0
class DiscountInline(FriendlyFieldsMixin, admin.TabularInline):
    verbose_name_plural = 'Скидки'
    model = CarDiscount
    extra = 0
class SpecificationInline(FriendlyFieldsMixin, admin.TabularInline):
    verbose_name_plural = 'Дополнительные характеристики'
    model=CarSpecification
    extra=0

@admin.register(Car)
class CarAdmin(SEOAdmin):
    list_per_page = 20
    autocomplete_fields = ['brand', 'category']
    actions=['show_cars','hide_cars','feature_cars']
    @admin.action(description='Показать выбранные автомобили')
    def show_cars(self,request,queryset):
        for car in queryset:car.active=True;car.save(update_fields=['active','updated_at'])
    @admin.action(description='Скрыть выбранные автомобили')
    def hide_cars(self,request,queryset):
        for car in queryset:car.active=False;car.save(update_fields=['active','updated_at'])
    @admin.action(description='Добавить в избранное')
    def feature_cars(self,request,queryset):
        for car in queryset:car.featured=True;car.save(update_fields=['featured','updated_at'])
    list_display = ['cover', 'name', 'brand', 'category', 'base_price', 'active', 'featured', 'sort_order', 'seo_warning','translation_status']
    list_display_links = ['cover', 'name']
    list_editable = ['base_price', 'active', 'featured', 'sort_order']
    list_filter = ['active', 'featured', 'brand', 'category', 'cities', 'transmission']
    search_fields = ['name', 'slug', 'legacy_id']
    filter_horizontal = ['cities', 'features']
    inlines = [ImageInline, PriceInline, DiscountInline, SpecificationInline,TranslationInline]
    fieldsets = [('Автомобиль — RU', {'fields': ('name', 'slug', 'legacy_path', 'legacy_id', 'brand', 'model_name', 'category', 'cities', 'base_price','deposit','mileage_limit', 'active', 'featured', 'accepts_requests', 'sort_order')}), ('Характеристики', {'fields': ('year', 'engine', 'transmission', 'drive','fuel', 'seats','doors', 'color', 'features', 'description')}), SEO_FIELDSET]
    list_select_related = ['brand', 'category']
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('images')
    @admin.display(description='Фото')
    def cover(self, obj):
        photo=obj.main_image
        return format_html('<img class="admin-photo" src="{}" width="88" height="56" alt="">',photo.card_url) if photo else '—'

@admin.register(CarCategory)
class CategoryAdmin(SEOAdmin):
    search_fields = ['name']
    list_display = ['name', 'active', 'sort_order', 'seo_warning']
    list_editable = ['active', 'sort_order']
    fieldsets = [(None, {'fields': ('name', 'slug', 'description', 'active', 'sort_order')}), SEO_FIELDSET]
@admin.register(CarBrand)
class BrandAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(CarFeature)
class FeatureAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    search_fields = ['name']
@admin.register(CarSpecification)
class SpecificationAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    list_display=['car','name','value','sort_order']
    search_fields=['car__name','name','value']
    inlines=[TranslationInline]
@admin.register(CarPrice)
class TariffAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    list_display=['car','label','min_days','max_days','daily_price']
    inlines=[TranslationInline]
    search_fields=['car__name','label']
    autocomplete_fields=['car']

@admin.register(CarImage)
class PhotoAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    list_display=['car','alt','sort_order','is_main']
    list_filter=['car__cities','is_main']
    search_fields=['car__name','alt']
    inlines=[TranslationInline]
    fields=['car','original','alt','caption','sort_order','is_main']
    autocomplete_fields=['car']
    class Media:
        js=['admin/editor.js']
        css={'all':['admin/editor.css']}
