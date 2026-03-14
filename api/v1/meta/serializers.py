from rest_framework import serializers

from crm.models import DealStage, LeadSource, LeadStatus


class LeadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStatus
        fields = ["id", "name", "code", "order", "is_active", "is_final"]


class DealStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealStage
        fields = ["id", "name", "code", "order", "is_active", "is_final"]


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = ["id", "name", "code", "description", "is_active"]
