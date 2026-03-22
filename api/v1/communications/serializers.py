from rest_framework import serializers

from crm_communications.models import Conversation, DeliveryFailureQueue, Message, MessageAttachment, MessageAttemptLog


class ConversationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    contact_name = serializers.SerializerMethodField()
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    last_message_id = serializers.IntegerField(source="last_message.pk", read_only=True)

    def get_contact_name(self, obj):
        contact = getattr(obj, "contact", None)
        if contact is None:
            return ""
        full_name = f"{contact.first_name} {contact.last_name}".strip()
        return full_name or contact.email or f"Контакт #{contact.pk}"

    class Meta:
        model = Conversation
        fields = [
            "id",
            "channel",
            "subject",
            "status",
            "client",
            "client_name",
            "contact",
            "contact_name",
            "deal",
            "deal_title",
            "requires_manual_binding",
            "last_message_id",
            "last_message_direction",
            "last_message_preview",
            "last_message_at",
            "last_incoming_at",
            "last_outgoing_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class MessageAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    def get_file_url(self, obj):
        file_field = getattr(obj, "file", None)
        if not file_field:
            return ""
        try:
            return file_field.url
        except Exception:
            return ""

    class Meta:
        model = MessageAttachment
        fields = [
            "id",
            "original_name",
            "mime_type",
            "size_bytes",
            "content_id",
            "is_inline",
            "file_url",
            "created_at",
        ]


class MessageSerializer(serializers.ModelSerializer):
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    contact_name = serializers.SerializerMethodField()

    def get_contact_name(self, obj):
        contact = getattr(obj, "contact", None)
        if contact is None:
            return ""
        full_name = f"{contact.first_name} {contact.last_name}".strip()
        return full_name or contact.email or f"Контакт #{contact.pk}"

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "channel",
            "direction",
            "message_type",
            "status",
            "client",
            "client_name",
            "contact",
            "contact_name",
            "deal",
            "deal_title",
            "touch",
            "author_user",
            "external_sender_key",
            "external_recipient_key",
            "subject",
            "body_text",
            "body_html",
            "body_preview",
            "provider_message_id",
            "provider_chat_id",
            "provider_thread_key",
            "external_message_id",
            "in_reply_to",
            "references",
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
            "requires_manual_retry",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class MessageAttemptLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttemptLog
        fields = [
            "id",
            "message",
            "attempt_number",
            "transport",
            "started_at",
            "finished_at",
            "status",
            "error_class",
            "error_code",
            "error_message",
            "provider_response_payload",
            "scheduled_retry_at",
            "is_final",
            "created_at",
            "updated_at",
        ]


class DeliveryFailureQueueSerializer(serializers.ModelSerializer):
    message_preview = serializers.CharField(source="message.body_preview", read_only=True)
    message_subject = serializers.CharField(source="message.subject", read_only=True)
    conversation_id = serializers.IntegerField(source="message.conversation_id", read_only=True)
    channel = serializers.CharField(source="message.channel", read_only=True)
    message_status = serializers.CharField(source="message.status", read_only=True)
    client = serializers.IntegerField(source="message.client_id", read_only=True)
    client_name = serializers.CharField(source="message.client.name", read_only=True)
    contact = serializers.IntegerField(source="message.contact_id", read_only=True)
    contact_name = serializers.SerializerMethodField()
    deal = serializers.IntegerField(source="message.deal_id", read_only=True)
    deal_title = serializers.CharField(source="message.deal.title", read_only=True)

    def get_contact_name(self, obj):
        contact = getattr(getattr(obj, "message", None), "contact", None)
        if contact is None:
            return ""
        full_name = f"{contact.first_name} {contact.last_name}".strip()
        return full_name or contact.email or f"Контакт #{contact.pk}"

    class Meta:
        model = DeliveryFailureQueue
        fields = [
            "id",
            "message",
            "message_subject",
            "message_preview",
            "conversation_id",
            "channel",
            "message_status",
            "client",
            "client_name",
            "contact",
            "contact_name",
            "deal",
            "deal_title",
            "failure_type",
            "opened_at",
            "last_attempt_log",
            "resolution_status",
            "assigned_to",
            "resolved_at",
            "resolution_comment",
            "created_at",
            "updated_at",
        ]


class ConversationBindSerializer(serializers.Serializer):
    client = serializers.IntegerField(required=False, allow_null=True)
    contact = serializers.IntegerField(required=False, allow_null=True)
    deal = serializers.IntegerField(required=False, allow_null=True)
    route_type = serializers.CharField(required=False, allow_blank=True, default="")
    route_key = serializers.CharField(required=False, allow_blank=True, default="")


class ConversationSendSerializer(serializers.Serializer):
    subject = serializers.CharField(required=False, allow_blank=True, default="")
    body_text = serializers.CharField(required=False, allow_blank=True, default="")
    body_html = serializers.CharField(required=False, allow_blank=True, default="")
    recipient = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not str(attrs.get("subject") or "").strip() and not str(attrs.get("body_text") or attrs.get("body_html") or "").strip():
            raise serializers.ValidationError("Укажите тему или текст сообщения.")
        return attrs


class DeliveryFailureRetrySerializer(serializers.Serializer):
    recipient = serializers.CharField(required=False, allow_blank=True, default="")


class DeliveryFailureResolutionSerializer(serializers.Serializer):
    resolution_comment = serializers.CharField(required=False, allow_blank=True, default="")
