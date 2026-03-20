from rest_framework import serializers
from django.utils import timezone

from crm.models import Touch
from crm.models.activity import ActivityType, TaskStatus
from crm.models.touch import normalize_touch_channel_code


class TouchSerializer(serializers.ModelSerializer):
    has_follow_up_task = serializers.BooleanField(write_only=True, required=False, default=False)
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    result_option_name = serializers.CharField(source="result_option.name", read_only=True)
    result_option_code = serializers.CharField(source="result_option.code", read_only=True)
    result_option_group = serializers.CharField(source="result_option.group", read_only=True)
    result_option_class = serializers.CharField(source="result_option.result_class", read_only=True)
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
        has_follow_up_task = bool(attrs.pop("has_follow_up_task", False))
        lead = attrs.get("lead", getattr(self.instance, "lead", None))
        deal = attrs.get("deal", getattr(self.instance, "deal", None))
        client = attrs.get("client", getattr(self.instance, "client", None))
        contact = attrs.get("contact", getattr(self.instance, "contact", None))
        task = attrs.get("task", getattr(self.instance, "task", None))
        happened_at = attrs.get("happened_at", getattr(self.instance, "happened_at", None))
        channel = attrs.get("channel", getattr(self.instance, "channel", None))
        result_option = attrs.get("result_option", getattr(self.instance, "result_option", None))
        if not happened_at:
            raise serializers.ValidationError({"happened_at": "Укажите дату и время касания."})
        if lead is None and deal is None and client is None and contact is None and task is None:
            raise serializers.ValidationError({"lead": "Привяжите касание хотя бы к одному объекту CRM."})
        if task is not None and task.type != ActivityType.TASK:
            raise serializers.ValidationError({"task": "Можно привязать только задачу."})
        self._validate_result_option_channel(result_option, channel)
        if deal is not None:
            self._validate_deal_next_activity(attrs, deal, has_follow_up_task)
        return attrs

    def _validate_result_option_channel(self, result_option, channel):
        if result_option is None:
            return
        allowed_touch_types = list(getattr(result_option, "allowed_touch_types", []) or [])
        if not allowed_touch_types or channel is None:
            return
        channel_code = normalize_touch_channel_code(getattr(channel, "name", ""))
        if channel_code and channel_code in allowed_touch_types:
            return
        raise serializers.ValidationError(
            {
                "result_option": (
                    f'Результат "{result_option.name}" нельзя использовать с каналом '
                    f'"{getattr(channel, "name", "")}".'
                )
            }
        )

    def _validate_deal_next_activity(self, attrs, deal, has_follow_up_task=False):
        stage_code = str(getattr(getattr(deal, "stage", None), "code", "") or "").strip().lower()
        if stage_code in {"won", "failed"}:
            return
        if has_follow_up_task:
            return

        now = timezone.now()
        next_step_at = attrs.get("next_step_at", getattr(self.instance, "next_step_at", None))
        if next_step_at and next_step_at >= now:
            return

        has_future_touch = deal.touches.filter(next_step_at__gte=now)
        if self.instance is not None and self.instance.pk:
            has_future_touch = has_future_touch.exclude(pk=self.instance.pk)
        if has_future_touch.exists():
            return

        has_active_task = deal.activities.filter(
            type=ActivityType.TASK,
            status__in={TaskStatus.TODO, TaskStatus.IN_PROGRESS},
            due_at__gte=now,
        ).exists()
        if has_active_task:
            return

        raise serializers.ValidationError(
            {
                "next_step_at": (
                    "После касания по активной сделке должна остаться следующая активность: "
                    "укажите дату следующего шага, создайте задачу или закройте сделку."
                )
            }
        )

    class Meta:
        model = Touch
        fields = [
            "id",
            "happened_at",
            "channel",
            "channel_name",
            "result_option",
            "result_option_name",
            "result_option_code",
            "result_option_group",
            "result_option_class",
            "direction",
            "direction_label",
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
            "has_follow_up_task",
        ]
        read_only_fields = ("created_at", "updated_at")
