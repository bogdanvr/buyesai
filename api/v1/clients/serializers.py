from rest_framework import serializers
from django.utils import timezone

from crm.models import Client


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
        timestamp = timezone.localtime(timezone.now()).strftime("%d.%m.%Y %H:%M")
        entry = "\n".join([timestamp, f"Добавил: {self._actor_name()}", normalized_note])
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
            "industry",
            "okved",
            "okveds",
            "source",
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
