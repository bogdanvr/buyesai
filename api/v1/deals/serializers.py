from rest_framework import serializers

from crm.models import Deal


class DealSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    owner_name = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        owner = obj.owner
        if owner is None:
            return ""
        full_name = owner.get_full_name() if hasattr(owner, "get_full_name") else ""
        return full_name or getattr(owner, "username", "")

    class Meta:
        model = Deal
        fields = [
            "id",
            "title",
            "client",
            "client_name",
            "lead",
            "lead_title",
            "stage",
            "stage_name",
            "amount",
            "currency",
            "close_date",
            "closed_at",
            "is_won",
            "metadata",
            "owner",
            "owner_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("closed_at", "created_at", "updated_at")
