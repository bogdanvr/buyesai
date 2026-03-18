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
    failure_reason = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")

    def get_owner_name(self, obj):
        owner = obj.owner
        if owner is None:
            return ""
        full_name = owner.get_full_name() if hasattr(owner, "get_full_name") else ""
        return full_name or getattr(owner, "username", "")

    def _stage_requires_company(self, stage) -> bool:
        if stage is None:
            return False
        stage_code = str(getattr(stage, "code", "") or "").strip().lower()
        stage_name = str(getattr(stage, "name", "") or "").strip().lower()
        return stage_code == "thinking" or stage_name == "думают"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        source = attrs.get("source", getattr(self.instance, "source", None))
        client = attrs.get("client", getattr(self.instance, "client", None))
        stage = attrs.get("stage", getattr(self.instance, "stage", None))
        has_pending_task = bool(attrs.pop("has_pending_task", False))
        failure_reason = str(attrs.pop("failure_reason", "") or "").strip()
        metadata = dict(attrs.get("metadata") or getattr(self.instance, "metadata", {}) or {})
        if source is None:
            raise serializers.ValidationError({"source": "Источник сделки обязателен."})
        if self._stage_requires_company(stage) and client is None:
            raise serializers.ValidationError({"client": "Для этапа 'Думают' компания обязательна."})
        stage_code = str(getattr(stage, "code", "") or "").strip().lower()
        has_active_tasks = False
        if self.instance is not None:
            has_active_tasks = self.instance.activities.filter(type=ActivityType.TASK, is_done=False).exists()
        if stage_code not in {"won", "failed"} and not has_active_tasks and not has_pending_task:
            raise serializers.ValidationError(
                {"stage": "Сделка без активных задач допустима только в статусах 'Успешно' и 'Провален'."}
            )
        if stage_code == "failed":
            effective_failure_reason = failure_reason or str(metadata.get("failed_reason", "") or "").strip()
            if not effective_failure_reason:
                raise serializers.ValidationError({"failure_reason": "Укажите причину провала сделки."})
            metadata["failed_reason"] = effective_failure_reason
        elif failure_reason:
            metadata["failed_reason"] = failure_reason
        attrs["metadata"] = metadata
        attrs["currency"] = str(getattr(client, "currency", "") or "RUB").strip().upper() or "RUB"
        attrs["is_won"] = stage_code == "won"
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        metadata = getattr(instance, "metadata", {}) or {}
        data["failure_reason"] = str(metadata.get("failed_reason", "") or "")
        return data

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
            "failure_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("closed_at", "events", "created_at", "updated_at")
