from django.contrib import admin

from crm.models import Client, CommunicationChannel, Contact


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
    list_display = ("id", "first_name", "last_name", "client", "phone", "email", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("first_name", "last_name", "phone", "email", "client__name")
    autocomplete_fields = ("client",)


@admin.register(CommunicationChannel)
class CommunicationChannelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
