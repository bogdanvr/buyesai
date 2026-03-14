from rest_framework import serializers

from crm.models import Activity


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

    class Meta:
        model = Activity
        fields = [
            "id",
            "type",
            "subject",
            "description",
            "due_at",
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
