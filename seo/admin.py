from core.admin_forms import FriendlyFieldsMixin
from django.contrib import admin
from .models import Redirect
@admin.register(Redirect)
class RedirectAdmin(FriendlyFieldsMixin, admin.ModelAdmin):
    list_display = ['old_path', 'new_path', 'status_code', 'active']
    list_filter = ['active', 'status_code']
    search_fields = ['old_path', 'new_path']
