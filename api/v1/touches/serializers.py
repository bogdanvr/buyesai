from rest_framework import serializers

from crm.models import Touch
from crm.models.activity import ActivityType


class TouchSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    owner_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    task_subject = serializers.CharField(source="task.subject", read_only=True)
    company_name = serializers.SerializerMethodField()
    direction_label = serializers.CharField(source="get_direction_display", read_only=True)

    def get_owner_name(self, obj):
        owner = obj.owner
        if owner is None:
            return ""
        full_name = owner.get_full_name() if hasattr(owner, "get_full_name") else ""
        return str(full_name or getattr(owner, "username", "") or "").strip()

    def get_company_name(self, obj):
        if obj.client_id:
            return str(getattr(obj.client, "name", "") or "").strip()
        if obj.deal_id and getattr(obj.deal, "client", None):
            return str(obj.deal.client.name or "").strip()
        if obj.lead_id:
            if getattr(obj.lead, "client", None):
                return str(obj.lead.client.name or "").strip()
            return str(getattr(obj.lead, "company", "") or "").strip()
        if obj.contact_id and getattr(obj.contact, "client", None):
            return str(obj.contact.client.name or "").strip()
        return ""

    def get_contact_name(self, obj):
        contact = obj.contact
        if contact is None:
            return ""
        return f"{contact.first_name} {contact.last_name}".strip() or contact.phone or f"Контакт #{contact.pk}"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        lead = attrs.get("lead", getattr(self.instance, "lead", None))
        deal = attrs.get("deal", getattr(self.instance, "deal", None))
        client = attrs.get("client", getattr(self.instance, "client", None))
        contact = attrs.get("contact", getattr(self.instance, "contact", None))
        task = attrs.get("task", getattr(self.instance, "task", None))
        happened_at = attrs.get("happened_at", getattr(self.instance, "happened_at", None))
        if not happened_at:
            raise serializers.ValidationError({"happened_at": "Укажите дату и время касания."})
        if lead is None and deal is None and client is None and contact is None and task is None:
            raise serializers.ValidationError({"lead": "Привяжите касание хотя бы к одному объекту CRM."})
        if task is not None and task.type != ActivityType.TASK:
            raise serializers.ValidationError({"task": "Можно привязать только задачу."})
        return attrs

    class Meta:
        model = Touch
        fields = [
            "id",
            "happened_at",
            "channel",
            "channel_name",
            "direction",
            "direction_label",
            "result",
            "summary",
            "next_step",
            "next_step_at",
            "owner",
            "owner_name",
            "contact",
            "contact_name",
            "lead",
            "lead_title",
            "deal",
            "deal_title",
            "client",
            "client_name",
            "task",
            "task_subject",
            "company_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")
