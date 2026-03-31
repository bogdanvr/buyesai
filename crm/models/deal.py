from django.conf import settings
from django.db import models
from pathlib import Path

from crm.models.common import TimestampedModel


def truncate_upload_filename(filename: str, max_stem_length: int = 120) -> str:
    safe_name = Path(str(filename or "document")).name or "document"
    path = Path(safe_name)
    suffix = path.suffix or ""
    stem = path.stem or "document"
    if len(stem) <= max_stem_length:
        return f"{stem}{suffix}"
    return f"{stem[:max_stem_length]}{suffix}"


def deal_document_upload_to(instance, filename: str) -> str:
    deal_id = getattr(instance, "deal_id", None) or getattr(getattr(instance, "deal", None), "id", None) or "new"
    client_id = (
        getattr(getattr(instance, "deal", None), "client_id", None)
        or getattr(getattr(instance, "deal", None), "client", None) and getattr(instance.deal.client, "id", None)
        or "unassigned"
    )
    safe_name = truncate_upload_filename(filename)
    return f"company_{client_id}/deal_{deal_id}/{safe_name}"


class Deal(TimestampedModel):
    title = models.CharField(max_length=255, verbose_name="Сделка")
    description = models.TextField(blank=True, default="", verbose_name="Описание сделки")
    source = models.ForeignKey(
        "crm.LeadSource",
        related_name="deals",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Источник сделки",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="deals",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Клиент",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        related_name="deals",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Лид",
    )
    stage = models.ForeignKey(
        "crm.DealStage",
        related_name="deals",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Этап",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Сумма")
    currency = models.CharField(max_length=3, default="RUB", verbose_name="Валюта")
    close_date = models.DateField(blank=True, null=True, verbose_name="Плановая дата закрытия")
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата закрытия")
    is_won = models.BooleanField(default=False, verbose_name="Успешная")
    events = models.TextField(blank=True, default="", verbose_name="События")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Метаданные")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_deals",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный",
    )

    class Meta:
        verbose_name = "Сделка"
        verbose_name_plural = "Сделки"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["stage"]),
            models.Index(fields=["is_won"]),
            models.Index(fields=["close_date"]),
        ]

    def __str__(self):
        return self.title


class DealDocument(TimestampedModel):
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="documents",
        on_delete=models.CASCADE,
        verbose_name="Сделка",
    )
    file = models.FileField(upload_to=deal_document_upload_to, max_length=500, verbose_name="Файл")
    original_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Название файла")
    settlement_document = models.ForeignKey(
        "crm.SettlementDocument",
        related_name="deal_documents",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Документ взаиморасчетов",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_deal_documents",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Загрузил",
    )

    class Meta:
        verbose_name = "Документ сделки"
        verbose_name_plural = "Документы сделок"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["deal"]),
            models.Index(fields=["settlement_document"]),
        ]

    def __str__(self):
        return self.original_name or self.file.name.rsplit("/", 1)[-1] or f"Документ #{self.pk}"
