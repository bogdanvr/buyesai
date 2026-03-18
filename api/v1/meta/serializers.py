from rest_framework import serializers
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from crm.models import CommunicationChannel, DealStage, LeadSource, LeadStatus, TaskType


User = get_user_model()


class LeadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStatus
        fields = ["id", "name", "code", "order", "is_active", "is_final"]


class DealStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealStage
        fields = ["id", "name", "code", "order", "is_active", "is_final"]


class LeadSourceSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise serializers.ValidationError("Название источника обязательно.")
        return normalized

    def create(self, validated_data):
        name = validated_data["name"]
        base_code = slugify(name, allow_unicode=False).replace("-", "_") or "source"
        code = base_code
        index = 2
        while LeadSource.objects.filter(code=code).exists():
            code = f"{base_code}_{index}"
            index += 1
        validated_data["code"] = code
        validated_data.setdefault("is_active", True)
        return super().create(validated_data)

    class Meta:
        model = LeadSource
        fields = ["id", "name", "code", "description", "is_active"]
        read_only_fields = ("code",)


class CommunicationChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationChannel
        fields = ["id", "name", "is_active"]


class UserOptionSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        full_name = obj.get_full_name() if hasattr(obj, "get_full_name") else ""
        return str(full_name or getattr(obj, "username", "") or "").strip()

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name"]


class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = ["id", "name", "is_active"]
