from rest_framework import serializers

from crm.models import Contact


class ContactSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    contact_status_name = serializers.CharField(source="contact_status.name", read_only=True)

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
            "telegram",
            "whatsapp",
            "max_contact",
            "role",
            "role_name",
            "contact_status",
            "contact_status_name",
            "person_note",
            "is_primary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")
