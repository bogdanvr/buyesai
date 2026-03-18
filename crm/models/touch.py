from django.conf import settings
from django.db import models

from crm.models.common import TimestampedModel


class TouchDirection(models.TextChoices):
    INCOMING = "incoming", "Входящее"
    OUTGOING = "outgoing", "Исходящее"


class Touch(TimestampedModel):
    happened_at = models.DateTimeField(verbose_name="Дата и время")
    channel = models.ForeignKey(
        "crm.CommunicationChannel",
        related_name="touches",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Тип канала",
    )
    direction = models.CharField(
        max_length=16,
        choices=TouchDirection.choices,
        verbose_name="Направление",
    )
    result = models.TextField(blank=True, default="", verbose_name="Результат")
    summary = models.TextField(blank=True, default="", verbose_name="Краткое содержание")
    next_step = models.TextField(blank=True, default="", verbose_name="Следующий шаг")
    next_step_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата следующего шага")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_touches",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        related_name="touches",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Лид",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="touches",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="touches",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="touches",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    task = models.ForeignKey(
        "crm.Activity",
        related_name="touches",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Задача",
    )

    class Meta:
        verbose_name = "Касание"
        verbose_name_plural = "Касания"
        ordering = ("-happened_at", "-id")
        indexes = [
            models.Index(fields=["happened_at"]),
            models.Index(fields=["direction"]),
            models.Index(fields=["lead"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["client"]),
            models.Index(fields=["contact"]),
            models.Index(fields=["task"]),
        ]

    def __str__(self):
        return self.summary or self.result or f"Касание #{self.pk}"
