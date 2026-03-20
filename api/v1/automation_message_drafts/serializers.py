from rest_framework import serializers

from crm.models import AutomationMessageDraft


class AutomationMessageDraftSerializer(serializers.ModelSerializer):
    automation_rule_event_type = serializers.CharField(source="automation_rule.event_type", read_only=True)
    automation_rule_ui_priority = serializers.CharField(source="automation_rule.ui_priority", read_only=True)
    source_touch_summary = serializers.CharField(source="source_touch.summary", read_only=True)
    source_touch_happened_at = serializers.DateTimeField(source="source_touch.happened_at", read_only=True)
    proposed_channel_name = serializers.CharField(source="proposed_channel.name", read_only=True)
    owner_name = serializers.SerializerMethodField()
    acted_by_name = serializers.SerializerMethodField()
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    contact_name = serializers.SerializerMethodField()
    last_outbound_status = serializers.SerializerMethodField()
    last_outbound_channel = serializers.SerializerMethodField()
    last_outbound_recipient = serializers.SerializerMethodField()
    last_outbound_error = serializers.SerializerMethodField()
    last_outbound_sent_at = serializers.SerializerMethodField()

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

    def _last_outbound(self, obj):
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("outbound_messages")
        if prefetched:
            return prefetched[0]
        return obj.outbound_messages.order_by("-created_at", "-id").first()

    def get_last_outbound_status(self, obj):
        outbound = self._last_outbound(obj)
        return str(getattr(outbound, "status", "") or "").strip()

    def get_last_outbound_channel(self, obj):
        outbound = self._last_outbound(obj)
        return str(getattr(outbound, "channel_code", "") or "").strip()

    def get_last_outbound_recipient(self, obj):
        outbound = self._last_outbound(obj)
        return str(getattr(outbound, "recipient_display", "") or getattr(outbound, "recipient", "") or "").strip()

    def get_last_outbound_error(self, obj):
        outbound = self._last_outbound(obj)
        return str(getattr(outbound, "error_message", "") or "").strip()

    def get_last_outbound_sent_at(self, obj):
        outbound = self._last_outbound(obj)
        return getattr(outbound, "sent_at", None)

    class Meta:
        model = AutomationMessageDraft
        fields = [
            "id",
            "status",
            "title",
            "message_subject",
            "message_text",
            "source_event_type",
            "automation_rule",
            "automation_rule_event_type",
            "automation_rule_ui_priority",
            "source_touch",
            "source_touch_summary",
            "source_touch_happened_at",
            "proposed_channel",
            "proposed_channel_name",
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
            "acted_by",
            "acted_by_name",
            "acted_at",
            "last_outbound_status",
            "last_outbound_channel",
            "last_outbound_recipient",
            "last_outbound_error",
            "last_outbound_sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
