from decimal import Decimal

from django.urls import reverse
from rest_framework import serializers

from crm.models import Client, SettlementAllocation, SettlementContract, SettlementDocument


class SettlementAllocationHistorySerializer(serializers.ModelSerializer):
    source_document_id = serializers.IntegerField(source="source_document.id", read_only=True)
    source_document_type = serializers.CharField(source="source_document.document_type", read_only=True)
    source_document_type_label = serializers.CharField(source="source_document.get_document_type_display", read_only=True)
    source_document_number = serializers.CharField(source="source_document.number", read_only=True)
    source_document_title = serializers.CharField(source="source_document.title", read_only=True)
    target_document_id = serializers.IntegerField(source="target_document.id", read_only=True)
    target_document_type = serializers.CharField(source="target_document.document_type", read_only=True)
    target_document_type_label = serializers.CharField(source="target_document.get_document_type_display", read_only=True)
    target_document_number = serializers.CharField(source="target_document.number", read_only=True)
    target_document_title = serializers.CharField(source="target_document.title", read_only=True)

    class Meta:
        model = SettlementAllocation
        fields = [
            "id",
            "amount",
            "allocated_at",
            "note",
            "source_document_id",
            "source_document_type",
            "source_document_type_label",
            "source_document_number",
            "source_document_title",
            "target_document_id",
            "target_document_type",
            "target_document_type_label",
            "target_document_number",
            "target_document_title",
            "created_at",
            "updated_at",
        ]


class SettlementContractSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = SettlementContract
        fields = [
            "id",
            "client",
            "client_name",
            "title",
            "number",
            "currency",
            "hourly_rate",
            "advance_percent",
            "warranty_days",
            "claim_response_days",
            "termination_notice_days",
            "start_date",
            "end_date",
            "note",
            "generator_payload",
            "file",
            "file_url",
            "download_url",
            "original_name",
            "file_size",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj):
        file_field = getattr(obj, "file", None)
        if not file_field:
            return ""
        try:
            return file_field.url
        except Exception:
            return ""

    def get_download_url(self, obj):
        if not getattr(obj, "file", None):
            return ""
        request = self.context.get("request")
        relative_url = reverse("settlement-contracts-download", kwargs={"pk": obj.pk})
        return request.build_absolute_uri(relative_url) if request is not None else relative_url

    def get_file_size(self, obj):
        file_field = getattr(obj, "file", None)
        if not file_field:
            return 0
        try:
            return int(file_field.size or 0)
        except Exception:
            return 0


class SettlementContractGenerateSerializer(serializers.Serializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    advance_percent = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal("0.00"))
    hourly_rate = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))
    warranty_days = serializers.IntegerField(min_value=1, default=31)
    claim_response_days = serializers.IntegerField(min_value=1, default=5)
    termination_notice_days = serializers.IntegerField(min_value=1, default=5)


class SettlementDocumentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    contract_name = serializers.SerializerMethodField()
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    document_type_label = serializers.CharField(source="get_document_type_display", read_only=True)
    flow_direction_label = serializers.CharField(source="get_flow_direction_display", read_only=True)
    realization_status_label = serializers.CharField(source="normalized_realization_status_label", read_only=True)
    closed_amount = serializers.SerializerMethodField()
    allocation_history = serializers.SerializerMethodField()
    can_allocate_as_source = serializers.BooleanField(read_only=True)
    can_allocate_as_target = serializers.BooleanField(read_only=True)
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    def get_contract_name(self, obj):
        contract = getattr(obj, "contract", None)
        if contract is None:
            return "Без договора"
        return str(contract.title or contract.number or f"Договор #{contract.pk}").strip()

    def get_closed_amount(self, obj):
        return Decimal(obj.amount or 0) - Decimal(obj.open_amount or 0)

    def get_allocation_history(self, obj):
        incoming = [
            {
                **SettlementAllocationHistorySerializer(item, context=self.context).data,
                "history_role": "incoming",
            }
            for item in obj.incoming_allocations.all()
        ]
        outgoing = [
            {
                **SettlementAllocationHistorySerializer(item, context=self.context).data,
                "history_role": "outgoing",
            }
            for item in obj.outgoing_allocations.all()
        ]
        history = incoming + outgoing
        history.sort(key=lambda item: (item.get("allocated_at") or "", item.get("id") or 0), reverse=True)
        return history

    def get_file_url(self, obj):
        file_field = getattr(obj, "file", None)
        if not file_field:
            return ""
        try:
            return file_field.url
        except Exception:
            return ""

    def get_download_url(self, obj):
        if not getattr(obj, "file", None):
            return ""
        request = self.context.get("request")
        relative_url = reverse("settlement-documents-download", kwargs={"pk": obj.pk})
        return request.build_absolute_uri(relative_url) if request is not None else relative_url

    def get_file_size(self, obj):
        file_field = getattr(obj, "file", None)
        if not file_field:
            return 0
        try:
            return int(file_field.size or 0)
        except Exception:
            return 0

    def validate(self, attrs):
        attrs = super().validate(attrs)
        uploaded_file = attrs.get("file")
        original_name = str(attrs.get("original_name") or "").strip()
        document_type = attrs.get("document_type") or getattr(self.instance, "document_type", "")
        realization_status = attrs.get("realization_status")
        client = attrs.get("client") or getattr(self.instance, "client", None)
        contract = attrs.get("contract") if "contract" in attrs else getattr(self.instance, "contract", None)
        deal = attrs.get("deal") if "deal" in attrs else getattr(self.instance, "deal", None)

        if document_type in {"advance", "advance_offset"}:
            raise serializers.ValidationError(
                {"document_type": "Документы 'Аванс' и 'Зачет аванса' больше не создаются отдельно. Используйте оплату и закрытие."}
            )

        if document_type == SettlementDocument.DocumentType.REALIZATION and deal is None:
            raise serializers.ValidationError({"deal": "Для акта сделка обязательна."})
        if contract is not None and client is not None and contract.client_id != client.id:
            raise serializers.ValidationError({"contract": "Договор должен принадлежать той же компании."})
        if deal is not None and client is not None and deal.client_id != client.id:
            raise serializers.ValidationError({"deal": "Сделка должна принадлежать той же компании."})

        if document_type == SettlementDocument.DocumentType.REALIZATION and not realization_status:
            attrs["realization_status"] = SettlementDocument.RealizationStatus.CREATED
        if document_type != SettlementDocument.DocumentType.REALIZATION:
            attrs["realization_status"] = ""

        if uploaded_file is not None:
            attrs["original_name"] = str(original_name or getattr(uploaded_file, "name", "") or "").strip()[:255]
        else:
            attrs["original_name"] = original_name[:255]
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.document_type == SettlementDocument.DocumentType.REALIZATION and not data.get("realization_status"):
            data["realization_status"] = instance.normalized_realization_status
        return data

    class Meta:
        model = SettlementDocument
        fields = [
            "id",
            "client",
            "client_name",
            "contract",
            "contract_name",
            "deal",
            "deal_title",
            "document_type",
            "document_type_label",
            "flow_direction",
            "flow_direction_label",
            "realization_status",
            "realization_status_label",
            "title",
            "number",
            "document_date",
            "due_date",
            "currency",
            "amount",
            "open_amount",
            "closed_amount",
            "note",
            "file",
            "file_url",
            "download_url",
            "original_name",
            "file_size",
            "can_allocate_as_source",
            "can_allocate_as_target",
            "allocation_history",
            "created_at",
            "updated_at",
        ]


class SettlementAllocationSerializer(serializers.ModelSerializer):
    source_document_label = serializers.SerializerMethodField()
    target_document_label = serializers.SerializerMethodField()

    def get_source_document_label(self, obj):
        source = getattr(obj, "source_document", None)
        if source is None:
            return ""
        return str(source.number or source.title or source.get_document_type_display()).strip()

    def get_target_document_label(self, obj):
        target = getattr(obj, "target_document", None)
        if target is None:
            return ""
        return str(target.number or target.title or target.get_document_type_display()).strip()

    class Meta:
        model = SettlementAllocation
        fields = [
            "id",
            "source_document",
            "source_document_label",
            "target_document",
            "target_document_label",
            "amount",
            "allocated_at",
            "note",
            "created_at",
            "updated_at",
        ]
