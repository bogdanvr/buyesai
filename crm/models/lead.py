from django.conf import settings
from django.db import models
import uuid

from crm.models.common import TimestampedModel


def normalize_lead_phone(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return ""
    if len(digits) == 10:
        digits = f"7{digits}"
    elif len(digits) == 11 and digits.startswith("8"):
        digits = f"7{digits[1:]}"
    return digits[:16]


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
    description = models.TextField(blank=True, default="", verbose_name="Описание")
    name = models.CharField(max_length=255, blank=True, default="", verbose_name="Имя")
    phone = models.CharField(max_length=64, blank=True, default="", verbose_name="Телефон")
    phone_normalized = models.CharField(
        max_length=16,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Телефон (нормализованный)",
    )
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
    sources = models.ManyToManyField(
        "crm.LeadSource",
        related_name="tracked_leads",
        blank=True,
        verbose_name="Источники",
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
    website_session = models.ForeignKey(
        "main.WebsiteSession",
        related_name="leads",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Веб-сессия",
    )
    payload = models.JSONField(default=dict, blank=True, verbose_name="Payload")
    utm_data = models.JSONField(default=dict, blank=True, verbose_name="UTM")
    history = models.JSONField(default=list, blank=True, verbose_name="История")
    events = models.TextField(blank=True, default="", verbose_name="События")
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
    assignment_notification_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Уведомление о новом лиде отправлено",
    )
    assignment_notification_token = models.CharField(
        max_length=32,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Токен принятия лида",
    )
    assignment_notification_accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Уведомление о новом лиде принято",
    )
    assignment_notification_email_escalated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Эскалация уведомления лида на email отправлена",
    )
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
            models.Index(fields=["website_session"]),
        ]

    def __str__(self):
        if self.title:
            return self.title
        if self.company:
            return self.company
        return f"Лид #{self.pk}"

    def save(self, *args, **kwargs):
        self.phone_normalized = normalize_lead_phone(self.phone)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            normalized_update_fields = set(update_fields)
            if "phone" in normalized_update_fields or "phone_normalized" in normalized_update_fields:
                normalized_update_fields.add("phone_normalized")
            kwargs["update_fields"] = list(normalized_update_fields)
        return super().save(*args, **kwargs)

    def ensure_assignment_notification_token(self) -> str:
        if not self.assignment_notification_token:
            self.assignment_notification_token = uuid.uuid4().hex
        return self.assignment_notification_token
