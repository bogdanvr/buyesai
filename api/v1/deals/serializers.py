from rest_framework import serializers

from crm.models import Deal
from crm.models.activity import ActivityType


class DealSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    source_code = serializers.CharField(source="source.code", read_only=True)
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    owner_name = serializers.SerializerMethodField()
    has_pending_task = serializers.BooleanField(write_only=True, required=False, default=False)

    def get_owner_name(self, obj):
        owner = obj.owner
        if owner is None:
            return ""
        full_name = owner.get_full_name() if hasattr(owner, "get_full_name") else ""
        return full_name or getattr(owner, "username", "")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        source = attrs.get("source", getattr(self.instance, "source", None))
        client = attrs.get("client", getattr(self.instance, "client", None))
        stage = attrs.get("stage", getattr(self.instance, "stage", None))
        has_pending_task = bool(attrs.pop("has_pending_task", False))
        if source is None:
            raise serializers.ValidationError({"source": "Источник сделки обязателен."})
        stage_code = str(getattr(stage, "code", "") or "").strip().lower()
        has_tasks = False
        if self.instance is not None:
            has_tasks = self.instance.activities.filter(type=ActivityType.TASK).exists()
        if stage_code not in {"won", "failed"} and not has_tasks and not has_pending_task:
            raise serializers.ValidationError(
                {"stage": "Сделка без задач допустима только в статусах 'Успешно' и 'Провален'."}
            )
        attrs["currency"] = str(getattr(client, "currency", "") or "RUB").strip().upper() or "RUB"
        attrs["is_won"] = stage_code == "won"
        return attrs

    class Meta:
        model = Deal
        fields = [
            "id",
            "title",
            "description",
            "source",
            "source_name",
            "source_code",
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
            "events",
            "metadata",
            "owner",
            "owner_name",
            "has_pending_task",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("closed_at", "events", "created_at", "updated_at")
