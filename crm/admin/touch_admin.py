from django.contrib import admin

from crm.models import Touch, TouchResult


@admin.register(TouchResult)
class TouchResultAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "group", "result_class", "sort_order", "is_active", "created_at")
    list_filter = ("group", "result_class", "requires_next_step", "requires_loss_reason", "is_active")
    search_fields = ("name", "code")


@admin.register(Touch)
class TouchAdmin(admin.ModelAdmin):
    list_display = ("id", "happened_at", "channel", "direction", "result_option", "owner", "client", "contact", "lead", "deal", "task")
    list_filter = ("direction", "channel", "result_option")
    search_fields = ("summary", "next_step", "result_option__name", "lead__title", "deal__title", "client__name", "contact__first_name", "contact__last_name", "task__subject")
    autocomplete_fields = ("channel", "result_option", "owner", "lead", "deal", "client", "contact", "task")
    readonly_fields = ("created_at", "updated_at")
