from django.contrib import admin
from core.admin import export_csv
from .models import BookingRequest

class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'city', 'status', 'created_at']
    list_filter = ['status', 'city', 'created_at', 'utm_source']
    search_fields = ['name', 'phone', 'comment', 'utm_campaign']
    readonly_fields = ['created_at', 'updated_at', 'source_page', 'landing_page', 'referrer', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'consent', 'consent_text']
    actions = [export_csv]
    date_hierarchy = 'created_at'
    list_select_related = ['city']

@admin.register(BookingRequest)
class BookingAdmin(LeadAdmin):
    list_display = ['name', 'phone', 'car', 'city', 'start_date', 'end_date', 'status', 'created_at']
    list_select_related = ['city', 'car']
