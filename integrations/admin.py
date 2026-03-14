from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from integrations.models import IntegrationWebhookEvent, UserIntegrationProfile


class UserIntegrationProfileInline(admin.StackedInline):
    model = UserIntegrationProfile
    can_delete = False
    extra = 0
    verbose_name_plural = "Интеграции"
    fields = ("phone", "telegram_chat_id")


User = get_user_model()


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (UserIntegrationProfileInline,)


@admin.register(IntegrationWebhookEvent)
class IntegrationWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "event_type", "external_id", "is_processed", "created_at")
    list_filter = ("source", "event_type", "is_processed")
    search_fields = ("external_id", "source", "event_type")
    readonly_fields = ("created_at", "processed_at")
