from django.contrib import admin

from crm_communications.models import (
    Conversation,
    ConversationRoute,
    DeliveryFailureQueue,
    Message,
    MessageAttachment,
    MessageAttemptLog,
    MessageWebhookEvent,
    ParticipantBinding,
)


class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0
    fields = ("original_name", "mime_type", "size_bytes", "is_inline", "file")
    readonly_fields = ("size_bytes",)


class MessageAttemptLogInline(admin.TabularInline):
    model = MessageAttemptLog
    extra = 0
    fields = ("attempt_number", "transport", "status", "error_class", "error_code", "scheduled_retry_at", "is_final")
    readonly_fields = ("attempt_number", "transport", "status", "error_class", "error_code", "scheduled_retry_at", "is_final")
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "channel",
        "subject",
        "client",
        "contact",
        "deal",
        "status",
        "requires_manual_binding",
        "last_message_at",
    )
    list_filter = ("channel", "status", "requires_manual_binding")
    search_fields = (
        "subject",
        "client__name",
        "contact__first_name",
        "contact__last_name",
        "contact__email",
        "deal__title",
        "last_message_preview",
    )
    autocomplete_fields = ("client", "contact", "deal", "last_message")
    readonly_fields = (
        "created_at",
        "updated_at",
        "last_message_direction",
        "last_message_preview",
        "last_message_at",
        "last_incoming_at",
        "last_outgoing_at",
    )


@admin.register(ConversationRoute)
class ConversationRouteAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "route_type", "route_key", "conversation", "client", "contact", "deal", "is_primary", "resolution_source")
    list_filter = ("channel", "route_type", "is_primary", "resolution_source")
    search_fields = ("route_key", "client__name", "contact__email", "deal__title", "conversation__subject")
    autocomplete_fields = ("conversation", "client", "contact", "deal", "resolved_by")
    readonly_fields = ("created_at", "updated_at", "resolved_at")


@admin.register(ParticipantBinding)
class ParticipantBindingAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "external_participant_key", "external_display_name", "client", "contact", "is_primary", "last_seen_at")
    list_filter = ("channel", "is_primary")
    search_fields = ("external_participant_key", "external_display_name", "client__name", "contact__email")
    autocomplete_fields = ("client", "contact")
    readonly_fields = ("created_at", "updated_at", "last_seen_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "channel",
        "direction",
        "status",
        "conversation",
        "client",
        "deal",
        "author_user",
        "queued_at",
        "sent_at",
        "received_at",
        "retry_count",
    )
    list_filter = ("channel", "direction", "status", "message_type", "requires_manual_retry")
    search_fields = (
        "subject",
        "body_text",
        "body_preview",
        "external_message_id",
        "provider_message_id",
        "provider_chat_id",
        "external_sender_key",
        "external_recipient_key",
        "conversation__subject",
        "client__name",
        "contact__email",
        "deal__title",
    )
    autocomplete_fields = ("conversation", "client", "contact", "deal", "touch", "author_user")
    readonly_fields = (
        "created_at",
        "updated_at",
        "queued_at",
        "next_attempt_at",
        "sending_started_at",
        "sent_at",
        "received_at",
        "delivered_at",
        "failed_at",
        "retry_count",
        "last_error_code",
        "last_error_message",
    )
    inlines = [MessageAttachmentInline, MessageAttemptLogInline]


@admin.register(MessageWebhookEvent)
class MessageWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "event_type", "external_event_id", "external_message_id", "processing_status", "processed_at", "created_at")
    list_filter = ("channel", "event_type", "processing_status")
    search_fields = ("external_event_id", "external_message_id", "error_message")
    readonly_fields = ("created_at", "updated_at", "processed_at", "payload", "error_message")


@admin.register(MessageAttemptLog)
class MessageAttemptLogAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "attempt_number", "transport", "status", "error_class", "error_code", "scheduled_retry_at", "is_final", "created_at")
    list_filter = ("transport", "status", "error_class", "is_final")
    search_fields = ("message__subject", "message__external_message_id", "error_code", "error_message")
    autocomplete_fields = ("message",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
        "scheduled_retry_at",
        "provider_response_payload",
    )


@admin.action(description="Перевести в работу")
def mark_failure_in_progress(modeladmin, request, queryset):
    queryset.update(resolution_status="in_progress", assigned_to=request.user)


@admin.action(description="Отметить как решённое")
def mark_failure_resolved(modeladmin, request, queryset):
    queryset.update(resolution_status="resolved", assigned_to=request.user)


@admin.action(description="Закрыть ошибку")
def mark_failure_closed(modeladmin, request, queryset):
    queryset.update(resolution_status="closed", assigned_to=request.user)


@admin.register(DeliveryFailureQueue)
class DeliveryFailureQueueAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "failure_type",
        "resolution_status",
        "assigned_to",
        "opened_at",
        "resolved_at",
        "last_attempt_log",
    )
    list_filter = ("failure_type", "resolution_status", "message__channel", "message__status")
    search_fields = (
        "message__subject",
        "message__body_preview",
        "message__external_message_id",
        "message__provider_message_id",
        "resolution_comment",
    )
    autocomplete_fields = ("message", "assigned_to", "last_attempt_log")
    readonly_fields = ("created_at", "updated_at", "opened_at", "resolved_at")
    actions = (mark_failure_in_progress, mark_failure_resolved, mark_failure_closed)
