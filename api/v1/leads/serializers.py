from rest_framework import serializers

from crm.models import Client, Lead, LeadStatus


LEAD_STATUS_TRANSITIONS = {
    "new": {"in_progress", "attempting_contact", "unqualified", "lost", "spam"},
    "attempting_contact": {"in_progress", "qualified", "unqualified", "lost", "spam"},
    "in_progress": {"qualified", "attempting_contact", "unqualified", "lost"},
    "qualified": {"converted", "lost"},
    "converted": {"archived"},
    "unqualified": {"qualified", "archived"},
    "lost": {"new", "in_progress", "attempting_contact", "qualified", "unqualified", "converted", "spam", "archived"},
    "spam": {"archived"},
    "archived": set(),
}


class LeadSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    source_code = serializers.CharField(source="source.code", read_only=True)
    source_names = serializers.SerializerMethodField()
    status_name = serializers.CharField(source="status.name", read_only=True)
    status_code = serializers.CharField(source="status.code", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    website_session_id = serializers.CharField(source="website_session.session_id", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id",
            "external_id",
            "title",
            "description",
            "name",
            "phone",
            "email",
            "company",
            "source",
            "source_name",
            "source_code",
            "sources",
            "source_names",
            "status",
            "status_name",
            "status_code",
            "client",
            "client_name",
            "website_session",
            "website_session_id",
            "payload",
            "utm_data",
            "history",
            "priority",
            "expected_value",
            "last_contact_at",
            "converted_at",
            "assigned_to",
            "assigned_to_name",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "created_at",
            "updated_at",
            "converted_at",
            "sources",
            "website_session",
            "website_session_id",
            "history",
        )

    def get_source_names(self, obj):
        return [source.name for source in obj.sources.all()]

    def get_assigned_to_name(self, obj):
        user = getattr(obj, "assigned_to", None)
        if user is None:
            return ""
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return str(full_name or getattr(user, "username", "") or "").strip()

    def _default_new_status(self):
        return LeadStatus.objects.filter(code="new").order_by("id").first()

    def validate(self, attrs):
        if "company" in attrs and isinstance(attrs["company"], str):
            attrs["company"] = attrs["company"].strip()

        instance = getattr(self, "instance", None)
        new_status = attrs.get("status")
        if instance is None or new_status is None:
            return attrs

        current_status = instance.status
        if current_status is None or current_status_id_equals(current_status, new_status):
            return attrs

        current_code = (current_status.code or "").strip()
        target_code = (new_status.code or "").strip()
        if not current_code or not target_code:
            return attrs

        allowed_targets = LEAD_STATUS_TRANSITIONS.get(current_code, set())
        if target_code not in allowed_targets:
            raise serializers.ValidationError(
                {
                    "status": (
                        f"Недопустимый переход статуса: {current_code} -> {target_code}. "
                        f"Разрешено: {', '.join(sorted(allowed_targets)) or 'нет'}."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        if not validated_data.get("status"):
            default_status = self._default_new_status()
            if default_status is not None:
                validated_data["status"] = default_status
        company_name = (validated_data.get("company") or "").strip()
        if company_name and not validated_data.get("client"):
            existing_client = (
                Client.objects.filter(name__iexact=company_name).order_by("id").first()
            )
            validated_data["client"] = (
                existing_client or Client.objects.create(name=company_name)
            )
            validated_data["company"] = company_name
        lead = super().create(validated_data)
        if lead.source_id:
            lead.sources.add(lead.source)
        return lead

    def update(self, instance, validated_data):
        lead = super().update(instance, validated_data)
        if lead.source_id:
            lead.sources.add(lead.source)
        return lead


def current_status_id_equals(current_status, new_status) -> bool:
    return getattr(current_status, "id", None) == getattr(new_status, "id", None)
