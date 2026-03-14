from django.contrib import admin

from crm.models import Lead, LeadSource, LeadStatus


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(LeadStatus)
class LeadStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "order", "is_active", "is_final")
    list_filter = ("is_active", "is_final")
    ordering = ("order",)
    search_fields = ("name", "code")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company", "phone", "status", "source", "assigned_to", "created_at")
    list_filter = ("status", "source", "priority", "created_at")
    search_fields = ("title", "name", "phone", "email", "company", "external_id")
    autocomplete_fields = ("client", "assigned_to", "created_by")
    readonly_fields = ("created_at", "updated_at", "converted_at")
