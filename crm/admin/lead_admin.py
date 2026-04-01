from django.contrib import admin

from crm.admin.site import crm_admin_site
from crm.models import Lead, LeadDocument, LeadSource, LeadStatus, TrafficSource


@admin.register(LeadSource, site=crm_admin_site)
class LeadSourceAdmin(admin.ModelAdmin):
    admin_group = "Лиды"
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(TrafficSource, site=crm_admin_site)
class TrafficSourceAdmin(admin.ModelAdmin):
    admin_group = "Лиды"
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(LeadStatus, site=crm_admin_site)
class LeadStatusAdmin(admin.ModelAdmin):
    admin_group = "Лиды"
    list_display = ("name", "code", "order", "is_active", "is_final")
    list_filter = ("is_active", "is_final")
    ordering = ("order",)
    search_fields = ("name", "code")
    filter_horizontal = ("touch_results",)


@admin.register(Lead, site=crm_admin_site)
class LeadAdmin(admin.ModelAdmin):
    admin_group = "Лиды"
    list_display = ("id", "title", "company", "phone", "status", "source", "assigned_to", "created_at")
    list_filter = ("status", "source", "sources", "priority", "created_at")
    search_fields = ("title", "description", "name", "phone", "email", "company", "external_id")
    autocomplete_fields = ("client", "assigned_to", "created_by", "website_session")
    filter_horizontal = ("sources",)
    readonly_fields = ("created_at", "updated_at", "converted_at", "history")


@admin.register(LeadDocument, site=crm_admin_site)
class LeadDocumentAdmin(admin.ModelAdmin):
    admin_group = "Лиды"
    list_display = ("id", "lead", "original_name", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("original_name", "lead__title", "lead__company", "lead__email")
    autocomplete_fields = ("lead", "uploaded_by")
