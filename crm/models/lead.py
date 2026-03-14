from django.conf import settings
from django.db import models

from crm.models.common import TimestampedModel


class LeadPriority(models.TextChoices):
    LOW = "low", "Низкий"
    MEDIUM = "medium", "Средний"
    HIGH = "high", "Высокий"


class Lead(TimestampedModel):
    external_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Внешний ID",
    )
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="Заголовок")
    name = models.CharField(max_length=255, blank=True, default="", verbose_name="Имя")
    phone = models.CharField(max_length=64, blank=True, default="", verbose_name="Телефон")
    email = models.EmailField(blank=True, default="", verbose_name="Email")
    company = models.CharField(max_length=255, blank=True, default="", verbose_name="Компания")
    source = models.ForeignKey(
        "crm.LeadSource",
        related_name="leads",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Источник",
    )
    status = models.ForeignKey(
        "crm.LeadStatus",
        related_name="leads",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Статус",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="leads",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Клиент",
    )
    payload = models.JSONField(default=dict, blank=True, verbose_name="Payload")
    utm_data = models.JSONField(default=dict, blank=True, verbose_name="UTM")
    priority = models.CharField(
        max_length=16,
        choices=LeadPriority.choices,
        default=LeadPriority.MEDIUM,
        verbose_name="Приоритет",
    )
    expected_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Ожидаемая сумма",
    )
    last_contact_at = models.DateTimeField(blank=True, null=True, verbose_name="Последний контакт")
    converted_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата конверсии")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_crm_leads",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_crm_leads",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Создал",
    )

    class Meta:
        verbose_name = "Лид"
        verbose_name_plural = "Лиды"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        if self.title:
            return self.title
        if self.company:
            return self.company
        return f"Лид #{self.pk}"
