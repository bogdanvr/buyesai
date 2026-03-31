from decimal import Decimal
import mimetypes

from django.http import FileResponse, Http404
from django.db.models import Q
from django.utils import timezone
from django.utils.http import content_disposition_header
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from api.v1.settlements.serializers import (
    SettlementAllocationSerializer,
    SettlementContractSerializer,
    SettlementDocumentSerializer,
)
from crm.models import SettlementAllocation, SettlementContract, SettlementDocument


ZERO = Decimal("0.00")


def _expected_receivable_key(document):
    deal_id = getattr(document, "deal_id", None)
    if deal_id:
        return ("deal", int(deal_id))
    contract_id = getattr(document, "contract_id", None)
    if contract_id:
        return ("contract", int(contract_id))
    return ("document", int(getattr(document, "pk", 0) or 0))


def build_settlement_stats(documents):
    today = timezone.localdate()
    expected_receivable = ZERO
    receivable = ZERO
    payable = ZERO
    advances_received = ZERO
    advances_issued = ZERO
    overdue = ZERO
    nearest_due_date = None
    invoices_by_key = {}
    realizations_by_key = {}

    for document in documents:
        open_amount = Decimal(document.open_amount or 0)
        if open_amount <= ZERO:
            continue
        if document.is_expected_receivable:
            key = _expected_receivable_key(document)
            invoices_by_key[key] = invoices_by_key.get(key, ZERO) + open_amount
        if document.is_receivable:
            receivable += open_amount
            key = _expected_receivable_key(document)
            realizations_by_key[key] = realizations_by_key.get(key, ZERO) + Decimal(document.amount or 0)
        if document.is_payable:
            payable += open_amount
        if document.is_advance_received:
            advances_received += open_amount
        if document.is_advance_issued:
            advances_issued += open_amount
        if (document.is_receivable or document.is_payable) and document.due_date:
            if nearest_due_date is None or document.due_date < nearest_due_date:
                nearest_due_date = document.due_date
            if document.due_date < today:
                overdue += open_amount

    for key, invoice_amount in invoices_by_key.items():
        expected_receivable += max(invoice_amount - realizations_by_key.get(key, ZERO), ZERO)

    balance = receivable + advances_issued - payable - advances_received
    return {
        "expected_receivable": expected_receivable,
        "receivable": receivable,
        "payable": payable,
        "advances_received": advances_received,
        "advances_issued": advances_issued,
        "overdue": overdue,
        "nearest_due_date": nearest_due_date,
        "balance": balance,
    }


class SettlementContractViewSet(ModelViewSet):
    serializer_class = SettlementContractSerializer

    def get_queryset(self):
        queryset = SettlementContract.objects.select_related("client").order_by("-created_at", "-id")
        client_id = self.request.query_params.get("client")
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset


class SettlementDocumentViewSet(ModelViewSet):
    serializer_class = SettlementDocumentSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = SettlementDocument.objects.select_related("client", "contract", "deal").prefetch_related(
            "incoming_allocations__source_document",
            "outgoing_allocations__target_document",
        ).order_by("-document_date", "-id")
        client_id = self.request.query_params.get("client")
        contract_id = self.request.query_params.get("contract")
        deal_id = self.request.query_params.get("deal")
        document_type = self.request.query_params.get("document_type")
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if document_type:
            queryset = queryset.filter(document_type=document_type)
        return queryset

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        instance = self.get_object()
        file_field = getattr(instance, "file", None)
        if not file_field:
            raise Http404("Файл не найден.")
        try:
            file_handle = file_field.open("rb")
        except FileNotFoundError as exc:
            raise Http404("Файл не найден.") from exc

        filename = instance.original_name or file_field.name.rsplit("/", 1)[-1]
        content_type, _ = mimetypes.guess_type(filename)
        response = FileResponse(file_handle, as_attachment=False, filename=filename, content_type=content_type or "application/octet-stream")
        response["Content-Disposition"] = content_disposition_header(False, filename)
        return response


class SettlementAllocationViewSet(ModelViewSet):
    serializer_class = SettlementAllocationSerializer

    def get_queryset(self):
        queryset = SettlementAllocation.objects.select_related(
            "source_document",
            "target_document",
            "source_document__client",
            "target_document__client",
        ).order_by("-allocated_at", "-id")
        client_id = self.request.query_params.get("client")
        document_id = self.request.query_params.get("document")
        if client_id:
            queryset = queryset.filter(source_document__client_id=client_id, target_document__client_id=client_id)
        if document_id:
            queryset = queryset.filter(Q(source_document_id=document_id) | Q(target_document_id=document_id))
        return queryset


class SettlementSummaryAPIView(APIView):
    def get(self, request):
        client_id = request.query_params.get("client")
        contract_id = request.query_params.get("contract")
        queryset = SettlementDocument.objects.select_related("contract", "client").order_by("-document_date", "-id")
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)

        documents = list(queryset)
        overview = build_settlement_stats(documents)
        contract_groups = {}
        for document in documents:
            key = document.contract_id or "no_contract"
            contract_groups.setdefault(key, []).append(document)

        contracts = []
        for key, items in contract_groups.items():
            first_document = items[0]
            contract = getattr(first_document, "contract", None)
            stats = build_settlement_stats(items)
            contracts.append(
                {
                    "contract_id": contract.pk if contract else None,
                    "title": str(getattr(contract, "title", "") or getattr(contract, "number", "") or "Без договора").strip(),
                    "number": str(getattr(contract, "number", "") or "").strip(),
                    "currency": str(getattr(contract, "currency", "") or first_document.currency or "").strip(),
                    "hourly_rate": getattr(contract, "hourly_rate", None),
                    "documents_count": len(items),
                    "stats": stats,
                }
            )
        contracts.sort(key=lambda item: (item["contract_id"] is None, str(item["title"] or "")))

        return Response(
            {
                "overview": overview,
                "contracts": contracts,
            }
        )
