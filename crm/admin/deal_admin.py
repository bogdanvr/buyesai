from django.contrib import admin

from crm.models import Deal, DealDocument, DealStage


@admin.register(DealStage)
class DealStageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "order", "is_active", "is_final")
    list_filter = ("is_active", "is_final")
    search_fields = ("name", "code")
    ordering = ("order",)


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "source", "client", "stage", "amount", "currency", "is_won", "close_date")
    list_filter = ("source", "stage", "is_won", "currency")
    search_fields = ("title", "description", "source__name", "client__name", "lead__title")
    autocomplete_fields = ("source", "client", "lead", "stage", "owner")
    readonly_fields = ("created_at", "updated_at", "closed_at")


@admin.register(DealDocument)
class DealDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "original_name", "deal", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("original_name", "deal__title", "deal__client__name")
    autocomplete_fields = ("deal", "uploaded_by")
    readonly_fields = ("created_at", "updated_at")
