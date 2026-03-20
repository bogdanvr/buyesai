from rest_framework import serializers

from crm.models import AutomationDraft


class AutomationDraftSerializer(serializers.ModelSerializer):
    automation_rule_event_type = serializers.CharField(source="automation_rule.event_type", read_only=True)
    automation_rule_ui_mode = serializers.CharField(source="automation_rule.ui_mode", read_only=True)
    automation_rule_ui_priority = serializers.CharField(source="automation_rule.ui_priority", read_only=True)
    source_touch_summary = serializers.CharField(source="source_touch.summary", read_only=True)
    source_touch_happened_at = serializers.DateTimeField(source="source_touch.happened_at", read_only=True)
    outcome_name = serializers.CharField(source="outcome.name", read_only=True)
    touch_result_name = serializers.CharField(source="touch_result.name", read_only=True)
    next_step_template_name = serializers.CharField(source="next_step_template.name", read_only=True)
    proposed_channel_name = serializers.CharField(source="proposed_channel.name", read_only=True)
    owner_name = serializers.SerializerMethodField()
    acted_by_name = serializers.SerializerMethodField()
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    contact_name = serializers.SerializerMethodField()
    task_subject = serializers.CharField(source="task.subject", read_only=True)

    def _user_name(self, user):
        if user is None:
            return ""
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return str(full_name or getattr(user, "username", "") or "").strip()

    def get_owner_name(self, obj):
        return self._user_name(obj.owner)

    def get_acted_by_name(self, obj):
        return self._user_name(obj.acted_by)

    def get_contact_name(self, obj):
        contact = obj.contact
        if contact is None:
            return ""
        full_name = f"{contact.first_name} {contact.last_name}".strip()
        return full_name or contact.phone or f"Контакт #{contact.pk}"

    class Meta:
        model = AutomationDraft
        fields = [
            "id",
            "draft_kind",
            "status",
            "title",
            "summary",
            "source_event_type",
            "automation_rule",
            "automation_rule_event_type",
            "automation_rule_ui_mode",
            "automation_rule_ui_priority",
            "source_touch",
            "source_touch_summary",
            "source_touch_happened_at",
            "outcome",
            "outcome_name",
            "touch_result",
            "touch_result_name",
            "next_step_template",
            "next_step_template_name",
            "proposed_channel",
            "proposed_channel_name",
            "proposed_direction",
            "proposed_next_step",
            "proposed_next_step_at",
            "owner",
            "owner_name",
            "lead",
            "lead_title",
            "deal",
            "deal_title",
            "client",
            "client_name",
            "contact",
            "contact_name",
            "task",
            "task_subject",
            "acted_by",
            "acted_by_name",
            "acted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
