from __future__ import annotations

from rest_framework import serializers

from integrations.models import LlmProviderAccount
from integrations.services.secrets import is_secret_encryption_configured


class LlmProviderAccountSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    clear_api_key = serializers.BooleanField(write_only=True, required=False, default=False)
    has_api_key = serializers.SerializerMethodField(read_only=True)
    api_key_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LlmProviderAccount
        fields = [
            "id",
            "name",
            "provider",
            "api_style",
            "base_url",
            "model",
            "organization",
            "project",
            "is_active",
            "use_for_touch_analysis",
            "priority",
            "api_key",
            "clear_api_key",
            "has_api_key",
            "api_key_masked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "has_api_key", "api_key_masked", "created_at", "updated_at"]

    def get_has_api_key(self, obj):
        return obj.has_api_key

    def get_api_key_masked(self, obj):
        return obj.api_key_masked

    def validate_priority(self, value):
        normalized = int(value or 0)
        return normalized if normalized > 0 else 100

    def validate(self, attrs):
        raw_api_key = str(attrs.get("api_key") or "").strip()
        clear_api_key = bool(attrs.get("clear_api_key", False))
        if (raw_api_key or clear_api_key) and not is_secret_encryption_configured():
            raise serializers.ValidationError({
                "api_key": "Нельзя сохранить ключ без INTEGRATIONS_SECRET_KEY на сервере.",
            })
        return attrs

    def create(self, validated_data):
        raw_api_key = str(validated_data.pop("api_key", "") or "").strip()
        validated_data.pop("clear_api_key", None)
        instance = LlmProviderAccount(**validated_data)
        if raw_api_key:
            instance.set_api_key(raw_api_key)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        raw_api_key = str(validated_data.pop("api_key", "") or "").strip()
        clear_api_key = bool(validated_data.pop("clear_api_key", False))
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if clear_api_key:
            instance.clear_api_key()
        elif raw_api_key:
            instance.set_api_key(raw_api_key)
        instance.save()
        return instance
