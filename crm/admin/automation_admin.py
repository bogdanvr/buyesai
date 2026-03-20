from django.contrib import admin

from crm.models import AutomationRule


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "create_touchpoint_mode",
        "default_outcome_code",
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
    search_fields = ("event_type", "default_outcome_code", "suggest_next_step_template")
