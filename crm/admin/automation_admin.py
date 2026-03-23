from django.contrib import admin

from crm.admin.site import crm_admin_site
from crm.models import (
    AutomationDraft,
    AutomationMessageDraft,
    AutomationOutboundMessage,
    AutomationQueueItem,
    AutomationRule,
    NextStepTemplate,
    OutcomeCatalog,
)


@admin.register(NextStepTemplate, site=crm_admin_site)
class NextStepTemplateAdmin(admin.ModelAdmin):
    admin_group = "Автоматизация"
    list_display = ("id", "code", "name")
    search_fields = ("code", "name")


@admin.register(OutcomeCatalog, site=crm_admin_site)
class OutcomeCatalogAdmin(admin.ModelAdmin):
    admin_group = "Автоматизация"
    list_display = ("id", "code", "name")
    search_fields = ("code", "name")


@admin.register(AutomationRule, site=crm_admin_site)
class AutomationRuleAdmin(admin.ModelAdmin):
    admin_group = "Автоматизация"
    list_display = (
        "id",
        "event_type",
        "ui_mode",
        "ui_priority",
        "show_in_attention_queue",
        "create_touchpoint_mode",
        "default_outcome",
        "next_step_template",
        "sort_order",
        "write_timeline",
        "show_in_summary",
        "create_message",
        "allow_auto_create_task",
        "require_manager_confirmation",
        "is_active",
    )
    list_filter = (
        "ui_mode",
        "ui_priority",
        "show_in_summary",
        "show_in_attention_queue",
        "create_touchpoint_mode",
        "write_timeline",
        "auto_open_panel",
        "create_message",
        "allow_auto_create_task",
        "require_manager_confirmation",
        "is_active",
    )
    autocomplete_fields = ("default_outcome", "next_step_template")
    search_fields = ("event_type", "default_outcome__name", "next_step_template__name", "next_step_template__code")


@admin.register(AutomationDraft, site=crm_admin_site)
class AutomationDraftAdmin(admin.ModelAdmin):
    admin_group = "Автоматизация"
    list_display = (
        "id",
        "draft_kind",
        "status",
        "title",
        "automation_rule",
        "source_touch",
        "deal",
        "client",
        "owner",
        "acted_by",
        "acted_at",
        "created_at",
    )
    list_filter = ("draft_kind", "status", "automation_rule", "created_at")
    autocomplete_fields = (
        "automation_rule",
        "source_touch",
        "outcome",
        "touch_result",
        "next_step_template",
        "proposed_channel",
        "owner",
        "lead",
        "deal",
        "client",
        "contact",
        "task",
        "acted_by",
    )
    search_fields = (
        "title",
        "summary",
        "source_event_type",
        "automation_rule__event_type",
        "source_touch__summary",
        "deal__title",
        "client__name",
    )


@admin.register(AutomationQueueItem, site=crm_admin_site)
class AutomationQueueItemAdmin(admin.ModelAdmin):
    admin_group = "Автоматизация"
    list_display = (
        "id",
        "item_kind",
        "status",
        "title",
        "automation_rule",
        "source_touch",
        "deal",
        "client",
        "owner",
        "created_task",
        "acted_by",
        "acted_at",
        "created_at",
    )
    list_filter = ("item_kind", "status", "automation_rule", "created_at")
    autocomplete_fields = (
        "automation_rule",
        "source_touch",
        "outcome",
        "touch_result",
        "next_step_template",
        "proposed_channel",
        "owner",
        "lead",
        "deal",
        "client",
        "contact",
        "task",
        "created_task",
        "acted_by",
    )
    search_fields = (
        "title",
        "summary",
        "recommended_action",
        "source_event_type",
        "automation_rule__event_type",
        "source_touch__summary",
        "deal__title",
        "client__name",
    )


@admin.register(AutomationMessageDraft, site=crm_admin_site)
class AutomationMessageDraftAdmin(admin.ModelAdmin):
    admin_group = "Автоматизация"
    list_display = (
        "id",
        "status",
        "title",
        "automation_rule",
        "source_touch",
        "deal",
        "client",
        "proposed_channel",
        "owner",
        "acted_by",
        "acted_at",
        "created_at",
    )
    list_filter = ("status", "automation_rule", "proposed_channel", "created_at")
    autocomplete_fields = (
        "automation_rule",
        "source_touch",
        "proposed_channel",
        "owner",
        "lead",
        "deal",
        "client",
        "contact",
        "acted_by",
    )
    search_fields = (
        "title",
        "message_subject",
        "message_text",
        "source_event_type",
        "automation_rule__event_type",
        "source_touch__summary",
        "deal__title",
        "client__name",
    )


@admin.register(AutomationOutboundMessage, site=crm_admin_site)
class AutomationOutboundMessageAdmin(admin.ModelAdmin):
    admin_group = "Автоматизация"
    list_display = (
        "id",
        "status",
        "channel_code",
        "title",
        "recipient_display",
        "provider",
        "message_draft",
        "deal",
        "client",
        "acted_by",
        "sent_at",
        "created_at",
    )
    list_filter = ("status", "channel_code", "provider", "created_at")
    autocomplete_fields = (
        "automation_rule",
        "message_draft",
        "source_touch",
        "owner",
        "lead",
        "deal",
        "client",
        "contact",
        "acted_by",
    )
    search_fields = (
        "title",
        "message_subject",
        "message_text",
        "source_event_type",
        "recipient",
        "recipient_display",
        "error_message",
        "deal__title",
        "client__name",
    )
