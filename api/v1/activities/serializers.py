from rest_framework import serializers
from django.utils import timezone

from crm.models import Activity
from crm.models.activity import ActivityType


class ActivitySerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    contact_name = serializers.SerializerMethodField()

    def get_contact_name(self, obj):
        contact = obj.contact
        if contact is None:
            return ""
        full_name = f"{contact.first_name} {contact.last_name}".strip()
        return full_name or contact.phone or f"Контакт #{contact.id}"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        activity_type = attrs.get("type", getattr(self.instance, "type", None))
        is_done = attrs.get("is_done", getattr(self.instance, "is_done", False))
        result = attrs.get("result", getattr(self.instance, "result", ""))
        if activity_type == ActivityType.TASK and is_done and not str(result or "").strip():
            raise serializers.ValidationError({"result": "Укажите результат завершения задачи."})
        return attrs

    def create(self, validated_data):
        if validated_data.get("is_done"):
            validated_data["completed_at"] = validated_data.get("completed_at") or timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        is_done = validated_data.get("is_done", instance.is_done)
        if is_done and not instance.completed_at and "completed_at" not in validated_data:
            validated_data["completed_at"] = timezone.now()
        if not is_done and "is_done" in validated_data:
            validated_data["completed_at"] = None
        return super().update(instance, validated_data)

    class Meta:
        model = Activity
        fields = [
            "id",
            "type",
            "subject",
            "description",
            "result",
            "due_at",
            "deadline_reminder_offset_minutes",
            "completed_at",
            "is_done",
            "lead",
            "lead_title",
            "deal",
            "deal_title",
            "client",
            "client_name",
            "contact",
            "contact_name",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("completed_at", "created_at", "updated_at")
