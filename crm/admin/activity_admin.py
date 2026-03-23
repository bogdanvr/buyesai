from django.contrib import admin

from crm.models import Activity, TaskCategory, TaskType, UserRole, UserRoleAssignment


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "role__name", "role__code")
    autocomplete_fields = ("user", "role")


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "group", "sort_order", "is_active", "created_at")
    list_filter = ("group", "is_active")
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")
    filter_horizontal = ("allowed_roles",)


@admin.register(TaskType)
class TaskTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "sort_order",
        "group",
        "auto_touch_on_done",
        "touch_result",
        "auto_task_on_done",
        "auto_task_type",
        "is_active",
        "created_at",
    )
    list_filter = ("category", "group", "auto_touch_on_done", "auto_task_on_done", "is_active")
    search_fields = ("name",)
    ordering = ("sort_order", "name")
    autocomplete_fields = ("category", "auto_task_type")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("type", "subject", "task_type", "communication_channel", "status", "priority", "client", "due_at", "created_at")
    list_filter = ("type", "status", "priority", "task_type", "communication_channel")
    search_fields = ("subject", "description")
    autocomplete_fields = ("lead", "deal", "client", "contact", "created_by", "task_type", "communication_channel", "related_touch")
    readonly_fields = ("created_at", "updated_at", "completed_at")
