from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from crm.models.client import truncate_upload_filename
from crm.models.common import TimestampedModel


ZERO_DECIMAL = Decimal("0.00")


def settlement_document_upload_to(instance, filename: str) -> str:
    client_id = getattr(instance, "client_id", None) or getattr(getattr(instance, "client", None), "id", None) or "new"
    safe_name = truncate_upload_filename(filename)
    return f"company_{client_id}/settlements/{safe_name}"


class SettlementContract(TimestampedModel):
    client = models.ForeignKey(
        "crm.Client",
        related_name="settlement_contracts",
        on_delete=models.CASCADE,
        verbose_name="Компания",
    )
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="Название договора")
    number = models.CharField(max_length=128, blank=True, default="", verbose_name="Номер договора")
    currency = models.CharField(max_length=3, default="RUB", verbose_name="Валюта")
    start_date = models.DateField(blank=True, null=True, verbose_name="Дата начала")
    end_date = models.DateField(blank=True, null=True, verbose_name="Дата окончания")
    note = models.TextField(blank=True, default="", verbose_name="Комментарий")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Договор взаиморасчетов"
        verbose_name_plural = "Договоры взаиморасчетов"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["client", "is_active"]),
        ]

    def __str__(self):
        base = self.number or self.title or f"Договор #{self.pk}"
        return str(base).strip()


class SettlementDocument(TimestampedModel):
    class DocumentType(models.TextChoices):
        INVOICE = "invoice", "Счет"
        REALIZATION = "realization", "Акт / накладная"
        SUPPLIER_RECEIPT = "supplier_receipt", "Поступление от поставщика"
        INCOMING_PAYMENT = "incoming_payment", "Оплата входящая"
        OUTGOING_PAYMENT = "outgoing_payment", "Оплата исходящая"
        DEBT_ADJUSTMENT = "debt_adjustment", "Корректировка долга"
        REFUND = "refund", "Возврат"
        ADVANCE = "advance", "Аванс"
        ADVANCE_OFFSET = "advance_offset", "Зачет аванса"

    class FlowDirection(models.TextChoices):
        INCOMING = "incoming", "Входящий"
        OUTGOING = "outgoing", "Исходящий"

    class RealizationStatus(models.TextChoices):
        CREATED = "created", "Создан"
        SENT = "sent_to_client", "Отправлен клиенту"
        SIGNED = "signed", "Подписан"

    client = models.ForeignKey(
        "crm.Client",
        related_name="settlement_documents",
        on_delete=models.CASCADE,
        verbose_name="Компания",
    )
    contract = models.ForeignKey(
        "crm.SettlementContract",
        related_name="documents",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Договор",
    )
    document_type = models.CharField(max_length=32, choices=DocumentType.choices, verbose_name="Тип документа")
    flow_direction = models.CharField(
        max_length=16,
        choices=FlowDirection.choices,
        blank=True,
        default="",
        verbose_name="Направление потока",
    )
    realization_status = models.CharField(
        max_length=32,
        choices=RealizationStatus.choices,
        blank=True,
        default="",
        verbose_name="Статус акта",
    )
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="Название")
    number = models.CharField(max_length=128, blank=True, default="", verbose_name="Номер документа")
    document_date = models.DateField(default=timezone.localdate, verbose_name="Дата документа")
    due_date = models.DateField(blank=True, null=True, verbose_name="Срок оплаты")
    currency = models.CharField(max_length=3, default="RUB", verbose_name="Валюта")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO_DECIMAL, verbose_name="Сумма")
    open_amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO_DECIMAL, verbose_name="Остаток")
    note = models.TextField(blank=True, default="", verbose_name="Комментарий")
    file = models.FileField(
        upload_to=settlement_document_upload_to,
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Файл",
    )
    original_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Название файла")

    class Meta:
        verbose_name = "Документ взаиморасчетов"
        verbose_name_plural = "Документы взаиморасчетов"
        ordering = ("-document_date", "-id")
        indexes = [
            models.Index(fields=["client", "document_type"]),
            models.Index(fields=["client", "contract"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        label = self.get_document_type_display()
        suffix = self.number or self.title or f"#{self.pk}"
        return f"{label} {suffix}".strip()

    @property
    def can_allocate_as_source(self) -> bool:
        return self.document_type in {
            self.DocumentType.INCOMING_PAYMENT,
            self.DocumentType.OUTGOING_PAYMENT,
            self.DocumentType.DEBT_ADJUSTMENT,
            self.DocumentType.REFUND,
            self.DocumentType.ADVANCE,
            self.DocumentType.ADVANCE_OFFSET,
        }

    @property
    def can_allocate_as_target(self) -> bool:
        return self.document_type in {
            self.DocumentType.REALIZATION,
            self.DocumentType.SUPPLIER_RECEIPT,
            self.DocumentType.ADVANCE,
        }

    @property
    def is_expected_receivable(self) -> bool:
        return self.document_type == self.DocumentType.INVOICE

    @property
    def is_receivable(self) -> bool:
        return self.document_type == self.DocumentType.REALIZATION

    @property
    def is_payable(self) -> bool:
        return self.document_type == self.DocumentType.SUPPLIER_RECEIPT

    @property
    def is_advance_received(self) -> bool:
        return (
            self.document_type == self.DocumentType.INCOMING_PAYMENT
            or (self.document_type == self.DocumentType.ADVANCE and self.flow_direction == self.FlowDirection.INCOMING)
        )

    @property
    def is_advance_issued(self) -> bool:
        return self.document_type == self.DocumentType.ADVANCE and self.flow_direction == self.FlowDirection.OUTGOING

    @property
    def closed_amount(self) -> Decimal:
        amount = Decimal(self.amount or ZERO_DECIMAL)
        open_amount = Decimal(self.open_amount or ZERO_DECIMAL)
        closed = amount - open_amount
        return closed if closed > ZERO_DECIMAL else ZERO_DECIMAL

    @property
    def normalized_realization_status(self) -> str:
        if self.document_type != self.DocumentType.REALIZATION:
            return ""
        return self.realization_status or self.RealizationStatus.CREATED

    @property
    def normalized_realization_status_label(self) -> str:
        if self.document_type != self.DocumentType.REALIZATION:
            return ""
        return self.RealizationStatus(self.normalized_realization_status).label

    def clean(self):
        amount = Decimal(self.amount or ZERO_DECIMAL)
        if amount <= ZERO_DECIMAL:
            raise ValidationError({"amount": "Сумма документа должна быть больше нуля."})

        if self.contract_id and self.contract and self.contract.client_id != self.client_id:
            raise ValidationError({"contract": "Договор должен принадлежать той же компании."})

        direction_required = {
            self.DocumentType.DEBT_ADJUSTMENT,
            self.DocumentType.REFUND,
            self.DocumentType.ADVANCE,
            self.DocumentType.ADVANCE_OFFSET,
        }
        if self.document_type in direction_required and not self.flow_direction:
            raise ValidationError({"flow_direction": "Укажите направление документа."})

        if self.document_type not in direction_required and self.flow_direction:
            raise ValidationError({"flow_direction": "Для этого типа направление не используется."})

        if self.document_type == self.DocumentType.REALIZATION and not self.realization_status:
            self.realization_status = self.RealizationStatus.CREATED

        if self.document_type != self.DocumentType.REALIZATION and self.realization_status:
            raise ValidationError({"realization_status": "Статус акта используется только для акта / накладной."})

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.currency:
            self.currency = (
                getattr(self.contract, "currency", "")
                or getattr(self.client, "currency", "")
                or "RUB"
            )
        creating = self.pk is None
        if creating and (self.open_amount in (None, "", ZERO_DECIMAL) or Decimal(self.open_amount or ZERO_DECIMAL) <= ZERO_DECIMAL):
            self.open_amount = self.amount
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creating:
                self.auto_allocate_on_create()
            self.recalculate_open_amount(save=True)

    def auto_allocate_on_create(self):
        if self.document_type == self.DocumentType.INCOMING_PAYMENT:
            self.auto_allocate_to_realizations()
            return
        if self.document_type == self.DocumentType.REALIZATION:
            self.auto_allocate_from_received_advances()

    def auto_allocate_to_realizations(self):
        current_open_amount = Decimal(self.open_amount or ZERO_DECIMAL)
        if current_open_amount <= ZERO_DECIMAL:
            return

        queryset = SettlementDocument.objects.select_for_update().filter(
            client_id=self.client_id,
            document_type=self.DocumentType.REALIZATION,
            open_amount__gt=ZERO_DECIMAL,
        ).exclude(pk=self.pk)
        if self.contract_id:
            queryset = queryset.filter(contract_id=self.contract_id)

        targets = sorted(
            queryset,
            key=lambda item: (
                item.due_date or date.max,
                item.document_date or date.max,
                item.pk or 0,
            ),
        )

        for target in targets:
            self.recalculate_open_amount(save=True)
            target.recalculate_open_amount(save=True)
            available_amount = Decimal(self.open_amount or ZERO_DECIMAL)
            target_open_amount = Decimal(target.open_amount or ZERO_DECIMAL)
            if available_amount <= ZERO_DECIMAL:
                break
            if target_open_amount <= ZERO_DECIMAL:
                continue

            allocation_amount = min(available_amount, target_open_amount)
            SettlementAllocation.objects.create(
                source_document=self,
                target_document=target,
                amount=allocation_amount,
                allocated_at=self.document_date or timezone.localdate(),
            )

    def auto_allocate_from_received_advances(self):
        current_open_amount = Decimal(self.open_amount or ZERO_DECIMAL)
        if current_open_amount <= ZERO_DECIMAL:
            return

        queryset = SettlementDocument.objects.select_for_update().filter(
            client_id=self.client_id,
            open_amount__gt=ZERO_DECIMAL,
        ).exclude(pk=self.pk).filter(
            models.Q(document_type=self.DocumentType.INCOMING_PAYMENT)
            | models.Q(
                document_type=self.DocumentType.ADVANCE,
                flow_direction=self.FlowDirection.INCOMING,
            )
        )
        if self.contract_id:
            queryset = queryset.filter(
                models.Q(contract_id=self.contract_id) | models.Q(contract_id__isnull=True)
            )

        sources = sorted(
            queryset,
            key=lambda item: (
                item.contract_id != self.contract_id if self.contract_id else False,
                item.document_date or date.max,
                item.pk or 0,
            ),
        )

        for source in sources:
            self.recalculate_open_amount(save=True)
            source.recalculate_open_amount(save=True)
            target_open_amount = Decimal(self.open_amount or ZERO_DECIMAL)
            source_open_amount = Decimal(source.open_amount or ZERO_DECIMAL)
            if target_open_amount <= ZERO_DECIMAL:
                break
            if source_open_amount <= ZERO_DECIMAL:
                continue

            allocation_amount = min(source_open_amount, target_open_amount)
            SettlementAllocation.objects.create(
                source_document=source,
                target_document=self,
                amount=allocation_amount,
                allocated_at=self.document_date or timezone.localdate(),
            )

    def recalculate_open_amount(self, save: bool = True):
        source_total = self.outgoing_allocations.aggregate(total=Sum("amount")).get("total") or ZERO_DECIMAL
        target_total = self.incoming_allocations.aggregate(total=Sum("amount")).get("total") or ZERO_DECIMAL
        new_open_amount = Decimal(self.amount or ZERO_DECIMAL) - Decimal(source_total) - Decimal(target_total)
        if new_open_amount < ZERO_DECIMAL:
            new_open_amount = ZERO_DECIMAL
        if Decimal(self.open_amount or ZERO_DECIMAL) != new_open_amount:
            self.open_amount = new_open_amount
            if save:
                SettlementDocument.objects.filter(pk=self.pk).update(open_amount=new_open_amount, updated_at=timezone.now())
        return new_open_amount


class SettlementAllocation(TimestampedModel):
    source_document = models.ForeignKey(
        "crm.SettlementDocument",
        related_name="outgoing_allocations",
        on_delete=models.CASCADE,
        verbose_name="Источник закрытия",
    )
    target_document = models.ForeignKey(
        "crm.SettlementDocument",
        related_name="incoming_allocations",
        on_delete=models.CASCADE,
        verbose_name="Закрываемый документ",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO_DECIMAL, verbose_name="Сумма распределения")
    allocated_at = models.DateField(default=timezone.localdate, verbose_name="Дата распределения")
    note = models.TextField(blank=True, default="", verbose_name="Комментарий")

    class Meta:
        verbose_name = "Распределение взаиморасчетов"
        verbose_name_plural = "Распределения взаиморасчетов"
        ordering = ("-allocated_at", "-id")
        indexes = [
            models.Index(fields=["source_document"]),
            models.Index(fields=["target_document"]),
        ]

    def __str__(self):
        return f"{self.source_document} -> {self.target_document}: {self.amount}"

    def clean(self):
        source = self.source_document
        target = self.target_document
        amount = Decimal(self.amount or ZERO_DECIMAL)

        if not source or not target:
            raise ValidationError("Укажите документы источника и назначения.")
        if source.pk == target.pk:
            raise ValidationError("Нельзя распределить документ сам в себя.")
        if amount <= ZERO_DECIMAL:
            raise ValidationError({"amount": "Сумма распределения должна быть больше нуля."})
        if source.client_id != target.client_id:
            raise ValidationError("Документы должны принадлежать одной компании.")
        if source.currency != target.currency:
            raise ValidationError("Валюта документов должна совпадать.")
        if not source.can_allocate_as_source:
            raise ValidationError({"source_document": "Этот документ нельзя использовать как источник закрытия."})
        if not target.can_allocate_as_target:
            raise ValidationError({"target_document": "Этот документ нельзя закрывать распределением."})
        if source.contract_id and target.contract_id and source.contract_id != target.contract_id:
            raise ValidationError("Документы с разными договорами можно связывать только если у одного из них договор не указан.")
        current_amount = ZERO_DECIMAL
        if self.pk:
            current_amount = SettlementAllocation.objects.filter(pk=self.pk).values_list("amount", flat=True).first() or ZERO_DECIMAL
        available_source = Decimal(source.open_amount or ZERO_DECIMAL) + Decimal(current_amount or ZERO_DECIMAL)
        available_target = Decimal(target.open_amount or ZERO_DECIMAL) + Decimal(current_amount or ZERO_DECIMAL)
        if available_source < amount:
            raise ValidationError({"amount": "Сумма распределения превышает остаток источника."})
        if available_target < amount:
            raise ValidationError({"amount": "Сумма распределения превышает остаток закрываемого документа."})

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.source_document.recalculate_open_amount(save=True)
            self.target_document.recalculate_open_amount(save=True)

    def delete(self, *args, **kwargs):
        source = self.source_document
        target = self.target_document
        with transaction.atomic():
            super().delete(*args, **kwargs)
            if source_id := getattr(source, "pk", None):
                refreshed_source = SettlementDocument.objects.filter(pk=source_id).first()
                if refreshed_source is not None:
                    refreshed_source.recalculate_open_amount(save=True)
            if target_id := getattr(target, "pk", None):
                refreshed_target = SettlementDocument.objects.filter(pk=target_id).first()
                if refreshed_target is not None:
                    refreshed_target.recalculate_open_amount(save=True)
