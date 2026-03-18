from django.contrib import admin

from crm.models import Touch


@admin.register(Touch)
class TouchAdmin(admin.ModelAdmin):
    list_display = ("id", "happened_at", "channel", "direction", "owner", "client", "contact", "lead", "deal", "task")
    list_filter = ("direction", "channel")
    search_fields = ("summary", "result", "next_step", "lead__title", "deal__title", "client__name", "contact__first_name", "contact__last_name", "task__subject")
    autocomplete_fields = ("channel", "owner", "lead", "deal", "client", "contact", "task")
    readonly_fields = ("created_at", "updated_at")
