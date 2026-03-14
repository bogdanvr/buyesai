from django.conf import settings
from django.db import models

from crm.models.common import TimestampedModel


class Deal(TimestampedModel):
    title = models.CharField(max_length=255, verbose_name="Сделка")
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
