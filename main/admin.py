from django.contrib import admin

from crm.admin.site import crm_admin_site
from main.models import (
    Case,
    Department,
    FormSubmission,
    Implementation,
    WebsiteSession,
    WebsiteSessionEvent,
)

@admin.register(Implementation)
@admin.register(Implementation, site=crm_admin_site)
class ImplementationAdmin(admin.ModelAdmin):
    admin_group = "Контент"
    list_display = ('step', 'title', 'period')


@admin.register(Case)
@admin.register(Case, site=crm_admin_site)
class CaseAdmin(admin.ModelAdmin):
    admin_group = "Контент"
    list_display = ('title', 'solution')


@admin.register(Department)
@admin.register(Department, site=crm_admin_site)
class DepartmentAdmin(admin.ModelAdmin):
    admin_group = "Контент"
    list_display = ('title',)


@admin.register(FormSubmission)
@admin.register(FormSubmission, site=crm_admin_site)
class FormSubmissionAdmin(admin.ModelAdmin):
    admin_group = "Сайт и формы"
    list_display = (
        "created_at",
        "form_type",
        "name",
        "phone",
        "company",
        "telegram_sent",
        "telegram_sent_count",
        "telegram_total_targets",
    )
    list_filter = ("form_type", "created_at", "telegram_sent")
    search_fields = ("name", "phone", "company", "message")
    readonly_fields = (
        "created_at",
        "utm_data",
        "telegram_sent",
        "telegram_sent_count",
        "telegram_total_targets",
        "telegram_errors",
    )


@admin.register(WebsiteSession)
@admin.register(WebsiteSession, site=crm_admin_site)
class WebsiteSessionAdmin(admin.ModelAdmin):
    admin_group = "Сайт и формы"
    list_display = (
        "session_id",
        "utm_source",
        "utm_campaign",
        "yclid",
        "client_id",
        "first_visit_at",
        "first_message_at",
    )
    search_fields = ("session_id", "utm_source", "utm_campaign", "yclid", "client_id", "landing_url", "referer")
    readonly_fields = ("first_visit_at", "first_message_at", "created_at", "updated_at")


@admin.register(WebsiteSessionEvent)
@admin.register(WebsiteSessionEvent, site=crm_admin_site)
class WebsiteSessionEventAdmin(admin.ModelAdmin):
    admin_group = "Сайт и формы"
    list_display = ("created_at", "session", "event_type", "page_url")
    list_filter = ("event_type", "created_at")
    search_fields = ("session__session_id", "event_type", "page_url")
    readonly_fields = ("created_at",)
