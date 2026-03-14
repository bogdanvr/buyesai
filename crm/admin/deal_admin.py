from django.contrib import admin

from crm.models import Deal, DealStage


@admin.register(DealStage)
class DealStageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "order", "is_active", "is_final")
    list_filter = ("is_active", "is_final")
    search_fields = ("name", "code")
    ordering = ("order",)


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "client", "stage", "amount", "currency", "is_won", "close_date")
    list_filter = ("stage", "is_won", "currency")
    search_fields = ("title", "client__name", "lead__title")
    autocomplete_fields = ("client", "lead", "stage", "owner")
    readonly_fields = ("created_at", "updated_at", "closed_at")
