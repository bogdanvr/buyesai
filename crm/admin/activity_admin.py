from django.contrib import admin

from crm.models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "subject", "client", "is_done", "due_at", "created_at")
    list_filter = ("type", "is_done")
    search_fields = ("subject", "description")
    autocomplete_fields = ("lead", "deal", "client", "contact", "created_by")
    readonly_fields = ("created_at", "updated_at", "completed_at")
