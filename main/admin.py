from django.contrib import admin

from main.models import (
    Case,
    Department,
    FormSubmission,
    Implementation,
    WebsiteSession,
    WebsiteSessionEvent,
)

@admin.register(Implementation)
class ImplementationAdmin(admin.ModelAdmin):
    list_display = ('step', 'title', 'period')


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'solution')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('title',)


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
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
class WebsiteSessionAdmin(admin.ModelAdmin):
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
class WebsiteSessionEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "session", "event_type", "page_url")
    list_filter = ("event_type", "created_at")
    search_fields = ("session__session_id", "event_type", "page_url")
    readonly_fields = ("created_at",)
