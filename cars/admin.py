from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from core.admin import SEOAdmin, SEO_FIELDSET, TranslationInline
from .models import Car, CarImage, CarPrice, CarDiscount, CarBrand, CarCategory, CarFeature

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

class ImageInline(admin.TabularInline):
    model = CarImage
    formset=ImageFormSet
    extra = 0
    fields = ['original', 'image', 'small', 'alt', 'caption', 'is_main', 'sort_order', 'legacy_url']
    readonly_fields = ['legacy_url', 'image', 'small']
class PriceInline(admin.TabularInline):
    model = CarPrice
    formset=PriceFormSet
    extra = 0
class DiscountInline(admin.TabularInline):
    model = CarDiscount
    extra = 0

@admin.register(Car)
class CarAdmin(SEOAdmin):
    list_display = ['name', 'brand', 'category', 'base_price', 'active', 'featured', 'sort_order', 'seo_warning']
    list_editable = ['base_price', 'active', 'featured', 'sort_order']
    list_filter = ['active', 'featured', 'brand', 'category', 'cities', 'transmission']
    search_fields = ['name', 'slug', 'legacy_id']
    filter_horizontal = ['cities', 'features']
    inlines = [ImageInline, PriceInline, DiscountInline, TranslationInline]
    fieldsets = [('Автомобиль', {'fields': ('name', 'slug', 'legacy_path', 'legacy_id', 'brand', 'model_name', 'category', 'cities', 'base_price', 'active', 'featured', 'accepts_requests', 'sort_order')}), ('Характеристики', {'fields': ('year', 'engine', 'transmission', 'drive', 'seats', 'color', 'features', 'description')}), SEO_FIELDSET]
    list_select_related = ['brand', 'category']

@admin.register(CarCategory)
class CategoryAdmin(SEOAdmin):
    list_display = ['name', 'active', 'sort_order', 'seo_warning']
    list_editable = ['active', 'sort_order']
    fieldsets = [(None, {'fields': ('name', 'slug', 'description', 'active', 'sort_order')}), SEO_FIELDSET]
admin.site.register(CarBrand)
admin.site.register(CarFeature)
