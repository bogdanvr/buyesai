from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from crm.admin.site import crm_admin_site
from integrations.models import (
    IntegrationWebhookEvent,
    LlmProviderAccount,
    PhoneCall,
    TelephonyEventLog,
    TelephonyProviderAccount,
    TelephonyUserMapping,
    UserIntegrationProfile,
)


class UserIntegrationProfileInline(admin.StackedInline):
    model = UserIntegrationProfile
    can_delete = False
    extra = 0
    verbose_name_plural = "Интеграции"
    fields = ("phone", "email", "telegram_chat_id")


User = get_user_model()


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    crm_admin_site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
@admin.register(User, site=crm_admin_site)
class CustomUserAdmin(UserAdmin):
    admin_group = "Пользователи и права"
    inlines = (UserIntegrationProfileInline,)


@admin.register(IntegrationWebhookEvent)
@admin.register(IntegrationWebhookEvent, site=crm_admin_site)
class IntegrationWebhookEventAdmin(admin.ModelAdmin):
    admin_group = "Интеграции"
    list_display = ("id", "source", "event_type", "external_id", "is_processed", "created_at")
    list_filter = ("source", "event_type", "is_processed")
    search_fields = ("external_id", "source", "event_type")
    readonly_fields = ("created_at", "processed_at")


@admin.register(TelephonyProviderAccount)
@admin.register(TelephonyProviderAccount, site=crm_admin_site)
class TelephonyProviderAccountAdmin(admin.ModelAdmin):
    admin_group = "Интеграции"
    list_display = ("provider", "enabled", "api_base_url", "default_owner", "last_connection_status", "updated_at")
    list_filter = ("provider", "enabled", "last_connection_status")
    search_fields = ("provider", "api_base_url")
    readonly_fields = ("created_at", "updated_at", "last_connection_checked_at")


@admin.register(LlmProviderAccount)
@admin.register(LlmProviderAccount, site=crm_admin_site)
class LlmProviderAccountAdmin(admin.ModelAdmin):
    admin_group = "Интеграции"
    list_display = ("name", "provider", "api_style", "model", "is_active", "use_for_touch_analysis", "priority", "updated_at")
    list_filter = ("provider", "api_style", "is_active", "use_for_touch_analysis")
    search_fields = ("name", "model", "base_url")
    readonly_fields = ("api_key_last4", "created_at", "updated_at")
    exclude = ("api_key_encrypted",)


@admin.register(TelephonyUserMapping)
@admin.register(TelephonyUserMapping, site=crm_admin_site)
class TelephonyUserMappingAdmin(admin.ModelAdmin):
    admin_group = "Интеграции"
    list_display = ("id", "provider_account", "crm_user", "novofon_full_name", "novofon_extension", "is_active", "is_default_owner")
    list_filter = ("provider_account", "is_active", "is_default_owner")
    search_fields = ("novofon_employee_id", "novofon_full_name", "novofon_extension", "crm_user__username")
    autocomplete_fields = ("provider_account", "crm_user")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PhoneCall)
@admin.register(PhoneCall, site=crm_admin_site)
class PhoneCallAdmin(admin.ModelAdmin):
    admin_group = "Интеграции"
    list_display = ("id", "provider", "external_call_id", "direction", "status", "transcription_status", "phone_from", "phone_to", "responsible_user", "started_at")
    list_filter = ("provider", "direction", "status", "transcription_status")
    search_fields = ("external_call_id", "phone_from", "phone_to", "client_phone_normalized")
    readonly_fields = ("created_at", "updated_at", "transcription_requested_at", "transcription_completed_at")


@admin.register(TelephonyEventLog)
@admin.register(TelephonyEventLog, site=crm_admin_site)
class TelephonyEventLogAdmin(admin.ModelAdmin):
    admin_group = "Интеграции"
    list_display = ("id", "provider", "event_type", "external_call_id", "status", "received_at", "processed_at", "retry_count")
    list_filter = ("provider", "status", "event_type")
    search_fields = ("external_event_id", "external_call_id", "deduplication_key")
    readonly_fields = ("received_at", "processed_at")
