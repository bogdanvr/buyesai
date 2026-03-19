from rest_framework import serializers

from crm.models import Contact


class ContactSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = Contact
        fields = [
            "id",
            "client",
            "client_name",
            "first_name",
            "last_name",
            "position",
            "phone",
            "email",
            "telegram_whatsapp",
            "role",
            "contact_status",
            "person_note",
            "is_primary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")
