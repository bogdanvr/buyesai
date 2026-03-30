from django.contrib import admin

from crm.admin.site import crm_admin_site
from crm.models import SettlementAllocation, SettlementContract, SettlementDocument


@admin.register(SettlementContract, site=crm_admin_site)
class SettlementContractAdmin(admin.ModelAdmin):
    admin_group = "Компании и контакты"
    list_display = ("id", "client", "number", "title", "currency", "is_active", "start_date", "end_date")
    list_filter = ("is_active", "currency")
    search_fields = ("client__name", "number", "title", "note")
    autocomplete_fields = ("client",)


@admin.register(SettlementDocument, site=crm_admin_site)
class SettlementDocumentAdmin(admin.ModelAdmin):
    admin_group = "Компании и контакты"
    list_display = ("id", "client", "contract", "document_type", "realization_status", "number", "document_date", "due_date", "amount", "open_amount", "currency")
    list_filter = ("document_type", "realization_status", "currency", "flow_direction")
    search_fields = ("client__name", "contract__number", "contract__title", "number", "title", "note")
    autocomplete_fields = ("client", "contract")


@admin.register(SettlementAllocation, site=crm_admin_site)
class SettlementAllocationAdmin(admin.ModelAdmin):
    admin_group = "Компании и контакты"
    list_display = ("id", "source_document", "target_document", "amount", "allocated_at")
    search_fields = ("source_document__number", "target_document__number", "source_document__client__name")
    autocomplete_fields = ("source_document", "target_document")
