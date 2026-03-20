from django.contrib import admin

from crm.models import AutomationRule, NextStepTemplate


@admin.register(NextStepTemplate)
class NextStepTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name")
    search_fields = ("code", "name")


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "create_touchpoint_mode",
        "default_outcome",
        "next_step_template",
        "sort_order",
        "write_timeline",
        "create_message",
        "require_manager_confirmation",
        "is_active",
    )
    list_filter = (
        "create_touchpoint_mode",
        "write_timeline",
        "create_message",
        "require_manager_confirmation",
        "is_active",
    )
    autocomplete_fields = ("default_outcome", "next_step_template")
    search_fields = ("event_type", "default_outcome__name", "next_step_template__name", "next_step_template__code")
