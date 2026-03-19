from django.contrib import admin

from crm.models import Activity, TaskType


@admin.register(TaskType)
class TaskTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sort_order",
        "group",
        "auto_touch_on_done",
        "touch_result",
        "auto_task_on_done",
        "auto_task_type",
        "is_active",
        "created_at",
    )
    list_filter = ("group", "auto_touch_on_done", "auto_task_on_done", "is_active")
    search_fields = ("name",)
    ordering = ("sort_order", "name")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("type", "subject", "task_type", "communication_channel", "status", "priority", "client", "due_at", "created_at")
    list_filter = ("type", "status", "priority", "task_type", "communication_channel")
    search_fields = ("subject", "description")
    autocomplete_fields = ("lead", "deal", "client", "contact", "created_by", "task_type", "communication_channel", "related_touch")
    readonly_fields = ("created_at", "updated_at", "completed_at")
