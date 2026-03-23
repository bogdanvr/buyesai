from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from crm.admin.site import crm_admin_site
from integrations.models import IntegrationWebhookEvent, UserIntegrationProfile


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
