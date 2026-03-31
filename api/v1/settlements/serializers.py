from datetime import date
from decimal import Decimal
import json

from django.urls import reverse
from rest_framework import serializers

from crm.models import Client, Contact, SettlementAllocation, SettlementContract, SettlementDocument
from crm.services.contract_generation import (
    DEFAULT_CLAIM_RESPONSE_DAYS,
    DEFAULT_OFFER_ACCEPTANCE_DAYS,
    DEFAULT_OFFER_ACCEPTANCE_TERM_DAYS,
    DEFAULT_OFFER_ADVANCE_PAYMENT_DAYS,
    DEFAULT_OFFER_FINAL_PAYMENT_DAYS,
    DEFAULT_OFFER_PENALTY_CAP_PERCENT,
    DEFAULT_OFFER_PENALTY_RATE,
    DEFAULT_TERMINATION_NOTICE_DAYS,
    DEFAULT_WARRANTY_DAYS,
    OFFER_AGREEMENT_TEMPLATE_CODE,
    SERVICE_AGREEMENT_TEMPLATE_CODE,
)


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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        generator_payload = attrs.get("generator_payload")
        if isinstance(generator_payload, str):
            try:
                generator_payload = json.loads(generator_payload)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError({"generator_payload": "Некорректный JSON параметров генерации."}) from exc
        if generator_payload is not None and not isinstance(generator_payload, dict):
            raise serializers.ValidationError({"generator_payload": "Параметры генерации должны быть объектом."})
        if isinstance(generator_payload, dict):
            attrs["generator_payload"] = self._validate_generator_payload(
                generator_payload,
                attrs,
                instance=self.instance,
            )
        uploaded_file = attrs.get("file")
        original_name_provided = "original_name" in attrs
        original_name = str(attrs.get("original_name") or "").strip()
        if uploaded_file is not None:
            attrs["original_name"] = str(original_name or getattr(uploaded_file, "name", "") or "").strip()[:255]
        elif original_name_provided:
            attrs["original_name"] = original_name[:255]
        return attrs

    def _validate_generator_payload(self, payload, attrs, *, instance=None):
        normalized = dict(payload)
        template_code = str(normalized.get("template_code") or "").strip()
        if template_code not in {SERVICE_AGREEMENT_TEMPLATE_CODE, OFFER_AGREEMENT_TEMPLATE_CODE}:
            raise serializers.ValidationError({"generator_payload": "Неизвестный шаблон договора."})

        if template_code == SERVICE_AGREEMENT_TEMPLATE_CODE:
            return {
                **normalized,
                "template_code": SERVICE_AGREEMENT_TEMPLATE_CODE,
                "customer_contact_id": normalized.get("customer_contact_id"),
                "executor_company_id": normalized.get("executor_company_id"),
            }

        acceptance_mode = str(normalized.get("offer_acceptance_mode") or "days").strip() or "days"
        explicit_date = normalized.get("offer_acceptance_deadline_date")
        if isinstance(explicit_date, date):
            explicit_date = explicit_date.isoformat()
        explicit_date = str(explicit_date or "").strip()
        if explicit_date:
            try:
                date.fromisoformat(explicit_date)
            except ValueError as exc:
                raise serializers.ValidationError({"generator_payload": "Дата акцепта должна быть в формате YYYY-MM-DD."}) from exc
        if acceptance_mode == "date" and not explicit_date:
            raise serializers.ValidationError({"generator_payload": "Для режима даты укажите дату акцепта."})
        if acceptance_mode not in {"days", "date"}:
            raise serializers.ValidationError({"generator_payload": "Некорректный режим срока акцепта."})

        return {
            **normalized,
            "template_code": OFFER_AGREEMENT_TEMPLATE_CODE,
            "customer_contact_id": normalized.get("customer_contact_id"),
            "executor_company_id": normalized.get("executor_company_id"),
            "offer_acceptance_mode": acceptance_mode,
            "offer_acceptance_term_days": int(normalized.get("offer_acceptance_term_days") or DEFAULT_OFFER_ACCEPTANCE_TERM_DAYS),
            "offer_acceptance_deadline_date": explicit_date,
            "offer_advance_payment_days": int(normalized.get("offer_advance_payment_days") or DEFAULT_OFFER_ADVANCE_PAYMENT_DAYS),
            "offer_final_payment_days": int(normalized.get("offer_final_payment_days") or DEFAULT_OFFER_FINAL_PAYMENT_DAYS),
            "offer_acceptance_days": int(normalized.get("offer_acceptance_days") or DEFAULT_OFFER_ACCEPTANCE_DAYS),
            "offer_penalty_rate": str(normalized.get("offer_penalty_rate") or DEFAULT_OFFER_PENALTY_RATE),
            "offer_penalty_cap_percent": str(normalized.get("offer_penalty_cap_percent") or DEFAULT_OFFER_PENALTY_CAP_PERCENT),
        }


class SettlementContractGenerateSerializer(serializers.Serializer):
    template_code = serializers.ChoiceField(choices=[
        (SERVICE_AGREEMENT_TEMPLATE_CODE, SERVICE_AGREEMENT_TEMPLATE_CODE),
        (OFFER_AGREEMENT_TEMPLATE_CODE, OFFER_AGREEMENT_TEMPLATE_CODE),
    ], default=SERVICE_AGREEMENT_TEMPLATE_CODE)
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    representative_contact = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.all(), allow_null=True, required=False)
    advance_percent = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal("0.00"))
    hourly_rate = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))
    warranty_days = serializers.IntegerField(min_value=1, default=DEFAULT_WARRANTY_DAYS, required=False)
    claim_response_days = serializers.IntegerField(min_value=1, default=DEFAULT_CLAIM_RESPONSE_DAYS, required=False)
    termination_notice_days = serializers.IntegerField(min_value=1, default=DEFAULT_TERMINATION_NOTICE_DAYS, required=False)
    offer_acceptance_term_days = serializers.IntegerField(min_value=1, default=DEFAULT_OFFER_ACCEPTANCE_TERM_DAYS, required=False)
    offer_acceptance_deadline_date = serializers.DateField(required=False, allow_null=True)
    offer_advance_payment_days = serializers.IntegerField(min_value=1, default=DEFAULT_OFFER_ADVANCE_PAYMENT_DAYS, required=False)
    offer_final_payment_days = serializers.IntegerField(min_value=1, default=DEFAULT_OFFER_FINAL_PAYMENT_DAYS, required=False)
    offer_acceptance_days = serializers.IntegerField(min_value=1, default=DEFAULT_OFFER_ACCEPTANCE_DAYS, required=False)
    offer_penalty_rate = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal("0.00"), default=DEFAULT_OFFER_PENALTY_RATE, required=False)
    offer_penalty_cap_percent = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal("0.00"), default=DEFAULT_OFFER_PENALTY_CAP_PERCENT, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        client = attrs.get("client")
        representative_contact = attrs.get("representative_contact")
        if representative_contact is not None and client is not None and representative_contact.client_id != client.pk:
            raise serializers.ValidationError({"representative_contact": "Контакт должен принадлежать выбранной компании."})
        template_code = attrs.get("template_code") or SERVICE_AGREEMENT_TEMPLATE_CODE
        if template_code == SERVICE_AGREEMENT_TEMPLATE_CODE:
            attrs["warranty_days"] = int(attrs.get("warranty_days") or DEFAULT_WARRANTY_DAYS)
        if template_code == OFFER_AGREEMENT_TEMPLATE_CODE:
            explicit_date = attrs.get("offer_acceptance_deadline_date")
            if explicit_date is not None and explicit_date < date.today():
                raise serializers.ValidationError({"offer_acceptance_deadline_date": "Дата акцепта не может быть в прошлом."})
        return attrs


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
