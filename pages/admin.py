from core.admin_forms import FriendlyFieldsMixin
from django.contrib import admin
from core.admin import SEOAdmin, SEO_FIELDSET, TranslationInline
from .models import Page, FAQ

@admin.register(Page)
class PageAdmin(SEOAdmin):
    list_display = ['title', 'path', 'active', 'legal_approved', 'seo_warning']
    search_fields = ['title', 'body']
    fieldsets = [(None, {'fields': ('title', 'slug', 'path', 'intro', 'body', 'active', 'show_in_footer', 'legal_approved')}), SEO_FIELDSET]
@admin.register(FAQ)
class FAQAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    inlines = [TranslationInline]
    list_display = ['question', 'city', 'page', 'car', 'active', 'sort_order']
    list_editable = ['active', 'sort_order']
    list_filter = ['active', 'city', 'page']
    search_fields = ['question', 'answer']
