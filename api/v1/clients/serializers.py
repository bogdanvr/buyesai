from rest_framework import serializers

from crm.models import Client


class ClientSerializer(serializers.ModelSerializer):
    leads_count = serializers.IntegerField(read_only=True)
    deals_count = serializers.IntegerField(read_only=True)

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

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "legal_name",
            "inn",
            "phone",
            "email",
            "website",
            "address",
            "industry",
            "okved",
            "okveds",
            "source",
            "notes",
            "events",
            "is_active",
            "leads_count",
            "deals_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("events", "created_at", "updated_at")
