from rest_framework import serializers
from django.utils.text import slugify

from crm.models import CommunicationChannel, DealStage, LeadSource, LeadStatus


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
