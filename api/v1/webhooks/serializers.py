from rest_framework import serializers

from integrations.models import IntegrationWebhookEvent


class WebhookCreateSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=64)
    event_type = serializers.CharField(max_length=128)
    external_id = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    payload = serializers.JSONField(required=False, default=dict)


class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationWebhookEvent
        fields = [
            "id",
            "source",
            "event_type",
            "external_id",
            "payload",
            "is_processed",
            "process_error",
            "created_at",
            "processed_at",
        ]
