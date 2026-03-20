from django.contrib import admin

from crm.models import Client, ClientDocument, CommunicationChannel, Contact, ContactRole, ContactStatus


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "phone",
        "email",
        "currency",
        "inn",
        "okved",
        "bank_name",
        "source",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "source", "currency")
    search_fields = ("name", "legal_name", "inn", "phone", "email", "address", "actual_address", "industry", "okved", "bank_name", "iban", "bik")
    inlines = (ContactInline,)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "client", "position", "role", "contact_status", "phone", "email", "is_primary")
    list_filter = ("is_primary", "role", "contact_status")
    search_fields = ("first_name", "last_name", "phone", "email", "telegram", "whatsapp", "max_contact", "role__name", "contact_status__name", "client__name")
    autocomplete_fields = ("client", "role", "contact_status")


@admin.register(ContactRole)
class ContactRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(ContactStatus)
class ContactStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(CommunicationChannel)
class CommunicationChannelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "original_name", "client", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("original_name", "client__name", "uploaded_by__username")
    autocomplete_fields = ("client", "uploaded_by")
    readonly_fields = ("created_at", "updated_at")
