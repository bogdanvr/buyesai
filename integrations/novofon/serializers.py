from django.contrib.auth import get_user_model
from rest_framework import serializers

from integrations.models import PhoneCall, TelephonyEventLog, TelephonyProviderAccount, TelephonyUserMapping
from integrations.novofon.selectors import build_webhook_url


User = get_user_model()


class TelephonyUserMappingSerializer(serializers.ModelSerializer):
    crm_user_name = serializers.SerializerMethodField()

    def get_crm_user_name(self, obj):
        user = getattr(obj, "crm_user", None)
        if user is None:
            return ""
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return str(full_name or getattr(user, "username", "") or "").strip()

    class Meta:
        model = TelephonyUserMapping
        fields = [
            "id",
            "crm_user",
            "crm_user_name",
            "novofon_employee_id",
            "novofon_extension",
            "novofon_full_name",
            "is_active",
            "is_default_owner",
            "created_at",
            "updated_at",
        ]


class TelephonyUserMappingWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    crm_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True, is_staff=True),
        allow_null=True,
        required=False,
    )
    novofon_employee_id = serializers.CharField()
    novofon_extension = serializers.CharField(required=False, allow_blank=True, default="")
    novofon_full_name = serializers.CharField(required=False, allow_blank=True, default="")
    is_active = serializers.BooleanField(required=False, default=True)
    is_default_owner = serializers.BooleanField(required=False, default=False)


class NovofonSettingsSerializer(serializers.ModelSerializer):
    has_api_secret = serializers.SerializerMethodField(read_only=True)
    webhook_url = serializers.SerializerMethodField(read_only=True)
    mappings = TelephonyUserMappingWriteSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = TelephonyProviderAccount
        fields = [
            "enabled",
            "api_key",
            "api_secret",
            "api_base_url",
            "webhook_path",
            "default_owner",
            "create_lead_for_unknown_number",
            "create_task_for_missed_call",
            "link_calls_to_open_deal_only",
            "allowed_virtual_numbers",
            "is_debug_logging_enabled",
            "webhook_shared_secret",
            "settings_json",
            "last_connection_checked_at",
            "last_connection_status",
            "last_connection_error",
            "has_api_secret",
            "webhook_url",
            "mappings",
        ]
        extra_kwargs = {
            "api_secret": {"write_only": True, "required": False, "allow_blank": True},
        }

    def get_has_api_secret(self, obj):
        return bool(str(obj.api_secret or "").strip())

    def get_webhook_url(self, obj):
        return build_webhook_url(obj)

    def validate_allowed_virtual_numbers(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Список виртуальных номеров должен быть массивом.")
        return [str(item or "").strip() for item in value if str(item or "").strip()]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["mappings"] = TelephonyUserMappingSerializer(
            instance.user_mappings.select_related("crm_user").order_by("novofon_full_name", "novofon_extension", "id"),
            many=True,
        ).data
        data.pop("api_secret", None)
        return data

    def update(self, instance, validated_data):
        mappings_data = validated_data.pop("mappings", None)
        api_secret = validated_data.pop("api_secret", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if api_secret not in (None, ""):
            instance.api_secret = api_secret
        instance.save()
        if mappings_data is not None:
            for item in mappings_data:
                mapping_id = item.get("id")
                employee_id = str(item.get("novofon_employee_id") or "").strip()
                mapping = None
                if mapping_id:
                    mapping = instance.user_mappings.filter(pk=mapping_id).first()
                if mapping is None and employee_id:
                    mapping = instance.user_mappings.filter(novofon_employee_id=employee_id).first()
                if mapping is None:
                    mapping = TelephonyUserMapping(provider_account=instance, novofon_employee_id=employee_id)
                mapping.crm_user = item.get("crm_user")
                mapping.novofon_extension = str(item.get("novofon_extension") or "").strip()
                mapping.novofon_full_name = str(item.get("novofon_full_name") or "").strip()
                mapping.is_active = bool(item.get("is_active", True))
                mapping.is_default_owner = bool(item.get("is_default_owner", False))
                mapping.save()
        return instance


class NovofonCallRequestSerializer(serializers.Serializer):
    ENTITY_TYPES = ("contact", "company", "lead", "deal")

    phone = serializers.CharField()
    entity_type = serializers.ChoiceField(choices=ENTITY_TYPES)
    entity_id = serializers.IntegerField()
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class NovofonCallImportRequestSerializer(serializers.Serializer):
    date_from = serializers.DateTimeField(required=False)
    date_till = serializers.DateTimeField(required=False)
    days = serializers.IntegerField(required=False, min_value=1, max_value=90, default=30)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=1000, default=500)
    max_records = serializers.IntegerField(required=False, min_value=1, max_value=20000, default=5000)
    include_ongoing_calls = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_till = attrs.get("date_till")
        if (date_from and not date_till) or (date_till and not date_from):
            raise serializers.ValidationError("Нужно передать обе даты: date_from и date_till.")
        return attrs


class PhoneCallSerializer(serializers.ModelSerializer):
    crm_user_name = serializers.SerializerMethodField()
    responsible_user_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="company.name", read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    deal_title = serializers.CharField(source="deal.title", read_only=True)

    def _user_name(self, user):
        if user is None:
            return ""
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return str(full_name or getattr(user, "username", "") or "").strip()

    def get_crm_user_name(self, obj):
        return self._user_name(getattr(obj, "crm_user", None))

    def get_responsible_user_name(self, obj):
        return self._user_name(getattr(obj, "responsible_user", None))

    def get_contact_name(self, obj):
        contact = getattr(obj, "contact", None)
        if contact is None:
            return ""
        full_name = f"{contact.first_name} {contact.last_name}".strip()
        return full_name or contact.phone or f"Контакт #{contact.pk}"

    class Meta:
        model = PhoneCall
        fields = [
            "id",
            "provider",
            "external_call_id",
            "external_parent_event_id",
            "direction",
            "status",
            "phone_from",
            "phone_to",
            "client_phone_normalized",
            "virtual_number",
            "crm_user",
            "crm_user_name",
            "responsible_user",
            "responsible_user_name",
            "contact",
            "contact_name",
            "company",
            "company_name",
            "lead",
            "lead_title",
            "deal",
            "deal_title",
            "started_at",
            "answered_at",
            "ended_at",
            "duration_sec",
            "talk_duration_sec",
            "recording_url",
            "raw_payload_last",
            "created_at",
            "updated_at",
        ]


class TelephonyEventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelephonyEventLog
        fields = [
            "id",
            "provider",
            "event_type",
            "external_event_id",
            "external_call_id",
            "deduplication_key",
            "status",
            "error_text",
            "received_at",
            "processed_at",
            "retry_count",
        ]
