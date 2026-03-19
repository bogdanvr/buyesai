from rest_framework import serializers
from django.utils import timezone

from crm.models import Client, CommunicationChannel, Contact


class ClientSerializer(serializers.ModelSerializer):
    leads_count = serializers.IntegerField(read_only=True)
    deals_count = serializers.IntegerField(read_only=True)
    note_draft = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")

    def _actor_name(self) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return "Система"
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return str(full_name or getattr(user, "username", "") or "Система").strip()

    def _merge_note(self, existing_notes: str, note_draft: str) -> str:
        normalized_note = str(note_draft or "").strip()
        if not normalized_note:
            return str(existing_notes or "").strip()
        timestamp = timezone.localtime(timezone.now()).strftime("%d.%m.%Y")
        entry = "\n".join([f"{timestamp} · Добавил: {self._actor_name()}", normalized_note])
        current = str(existing_notes or "").strip()
        return entry if not current else f"{entry}\n\n{current}"

    def validate_name(self, value):
        normalized = (value or "").strip()
        if not normalized:
            raise serializers.ValidationError("Название компании обязательно.")

        queryset = Client.objects.filter(name__iexact=normalized)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("Компания с таким названием уже существует.")

        return normalized

    def validate_work_rules(self, value):
        payload = value if isinstance(value, dict) else {}
        normalized = {
            "decision_maker_contact": None,
            "communication_channels": [],
            "payment_terms": str(payload.get("payment_terms", "") or "").strip(),
            "document_requirements": str(payload.get("document_requirements", "") or "").strip(),
            "approval_cycle": str(payload.get("approval_cycle", "") or "").strip(),
            "risks": str(payload.get("risks", "") or "").strip(),
            "preferences": str(payload.get("preferences", "") or "").strip(),
        }

        decision_maker_contact_id = payload.get("decision_maker_contact")
        if decision_maker_contact_id not in (None, "", 0, "0"):
            try:
                normalized["decision_maker_contact"] = int(decision_maker_contact_id)
            except (TypeError, ValueError):
                raise serializers.ValidationError("ЛПР указан некорректно.")

        raw_channel_ids = payload.get("communication_channels", payload.get("communication_channel"))
        if raw_channel_ids not in (None, "", [], ()):
            if not isinstance(raw_channel_ids, (list, tuple)):
                raw_channel_ids = [raw_channel_ids]
            seen_channel_ids = set()
            for channel_id in raw_channel_ids:
                if channel_id in (None, "", 0, "0"):
                    continue
                try:
                    normalized_channel_id = int(channel_id)
                except (TypeError, ValueError):
                    raise serializers.ValidationError("Канал связи указан некорректно.")
                if normalized_channel_id in seen_channel_ids:
                    continue
                seen_channel_ids.add(normalized_channel_id)
                normalized["communication_channels"].append(normalized_channel_id)

        client_id = None
        if self.instance is not None:
            client_id = self.instance.pk

        if normalized["decision_maker_contact"] is not None:
            if client_id is None:
                raise serializers.ValidationError("ЛПР можно выбрать только после создания контакта компании.")
            contact_exists = Contact.objects.filter(
                pk=normalized["decision_maker_contact"],
                client_id=client_id,
            ).exists()
            if not contact_exists:
                raise serializers.ValidationError("ЛПР должен быть выбран из контактов компании.")

        if normalized["communication_channels"]:
            channel_count = CommunicationChannel.objects.filter(
                pk__in=normalized["communication_channels"],
                is_active=True,
            ).count()
            if channel_count != len(normalized["communication_channels"]):
                raise serializers.ValidationError("Канал связи должен быть выбран из справочника.")

        return {key: value for key, value in normalized.items() if value not in (None, "")}

    def create(self, validated_data):
        note_draft = validated_data.pop("note_draft", "")
        validated_data["notes"] = self._merge_note("", note_draft)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        note_draft = validated_data.pop("note_draft", "")
        validated_data["notes"] = self._merge_note(instance.notes, note_draft)
        return super().update(instance, validated_data)

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "legal_name",
            "inn",
            "phone",
            "email",
            "currency",
            "website",
            "address",
            "actual_address",
            "bank_details",
            "iban",
            "bik",
            "bank_name",
            "industry",
            "okved",
            "okveds",
            "source",
            "work_rules",
            "notes",
            "note_draft",
            "events",
            "is_active",
            "leads_count",
            "deals_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("notes", "events", "created_at", "updated_at")
