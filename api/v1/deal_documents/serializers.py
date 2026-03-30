from django.urls import reverse
from rest_framework import serializers

from crm.models import Client, Deal, DealDocument


class DealDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    def get_uploaded_by_name(self, obj):
        user = getattr(obj, "uploaded_by", None)
        if user is None:
            return ""
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return str(full_name or getattr(user, "username", "") or "").strip()

    def get_file_url(self, obj):
        file_field = getattr(obj, "file", None)
        if not file_field:
            return ""
        try:
            return file_field.url
        except Exception:
            return ""

    def get_file_size(self, obj):
        file_field = getattr(obj, "file", None)
        if not file_field:
            return 0
        try:
            return int(file_field.size or 0)
        except Exception:
            return 0

    def get_download_url(self, obj):
        request = self.context.get("request")
        relative_url = reverse("deal-documents-download", kwargs={"pk": obj.pk})
        return request.build_absolute_uri(relative_url) if request is not None else relative_url

    def validate(self, attrs):
        attrs = super().validate(attrs)
        uploaded_file = attrs.get("file")
        if uploaded_file is None:
            raise serializers.ValidationError({"file": "Выберите файл."})
        original_name = str(attrs.get("original_name") or getattr(uploaded_file, "name", "") or "").strip()
        attrs["original_name"] = original_name[:255]
        return attrs

    class Meta:
        model = DealDocument
        fields = [
            "id",
            "deal",
            "file",
            "file_url",
            "download_url",
            "original_name",
            "file_size",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("uploaded_by", "created_at", "updated_at")


class DealActLineItemSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit = serializers.CharField(max_length=32, allow_blank=True, required=False, default="час")
    price = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_description(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise serializers.ValidationError("Заполните наименование услуги.")
        return normalized

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество должно быть больше нуля.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Стоимость должна быть больше нуля.")
        return value

    def validate_unit(self, value):
        normalized = str(value or "").strip()
        return normalized or "час"


class DealActGenerateSerializer(serializers.Serializer):
    deal = serializers.PrimaryKeyRelatedField(queryset=Deal.objects.select_related("client"))
    executor_company = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.filter(company_type=Client.CompanyType.OWN)
    )
    items = DealActLineItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Добавьте хотя бы одну строку акта.")
        return value
