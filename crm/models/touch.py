from django.conf import settings
from django.db import models
from django.utils.text import slugify

from crm.models.common import TimestampedModel


class TouchDirection(models.TextChoices):
    INCOMING = "incoming", "Входящее"
    OUTGOING = "outgoing", "Исходящее"


def normalize_touch_channel_code(value: str) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "телефон": "call",
        "звонок": "call",
        "call": "call",
        "email": "email",
        "e-mail": "email",
        "почта": "email",
        "whatsapp": "whatsapp",
        "ватсап": "whatsapp",
        "telegram": "telegram",
        "телеграм": "telegram",
        "meeting": "meeting",
        "встреча": "meeting",
        "proposal": "proposal",
        "предложение": "proposal",
        "коммерческое предложение": "proposal",
        "кп": "proposal",
        "document": "documents",
        "documents": "documents",
        "документ": "documents",
        "документы": "documents",
        "файлы": "documents",
    }
    if normalized in aliases:
        return aliases[normalized]
    slug = slugify(normalized).replace("-", "_")
    return aliases.get(slug, slug)


DIRECT_TOUCH_EVENT_TYPES_BY_RESULT_CODE = {
    "meeting_scheduled": "meeting_scheduled",
    "meeting_rescheduled": "meeting_rescheduled",
    "meeting_cancelled": "meeting_cancelled",
    "meeting_completed": "meeting_completed",
    "meeting_no_show": "meeting_no_show",
    "proposal_requested": "proposal_sent",
    "proposal_sent": "proposal_sent",
    "proposal_received": "proposal_received_by_client",
    "proposal_under_review": "proposal_received_by_client",
    "proposal_revision_requested": "proposal_revision_requested",
    "discount_requested": "proposal_revision_requested",
    "documents_requested": "documents_requested",
    "contract_sent": "contract_sent",
    "contract_under_review": "contract_under_review",
    "contract_revision_requested": "contract_revision_requested",
    "contract_agreed": "contract_agreed",
    "invoice_sent": "invoice_sent",
    "invoice_accepted": "invoice_received_by_client",
    "waiting_payment": "payment_waiting",
    "payment_confirmed": "payment_confirmed",
}


def resolve_touch_event_type(*, channel_code: str, direction: str, result_code: str = "") -> str:
    normalized_channel_code = normalize_touch_channel_code(channel_code)
    normalized_result_code = str(result_code or "").strip().lower()
    normalized_direction = str(direction or "").strip().lower()

    if not normalized_channel_code:
        return ""
    if normalized_channel_code == "call" and normalized_result_code == "no_answer":
        return "call_no_answer"
    if normalized_result_code in DIRECT_TOUCH_EVENT_TYPES_BY_RESULT_CODE:
        return DIRECT_TOUCH_EVENT_TYPES_BY_RESULT_CODE[normalized_result_code]
    if normalized_channel_code == "call":
        return "call_completed"
    if normalized_channel_code == "meeting":
        return "meeting_completed"
    if normalized_channel_code == "email":
        return f"email_{'received' if normalized_direction == TouchDirection.INCOMING else 'sent'}"
    if normalized_channel_code == "telegram":
        return f"telegram_message_{'received' if normalized_direction == TouchDirection.INCOMING else 'sent'}"
    if normalized_channel_code == "whatsapp":
        return f"whatsapp_message_{'received' if normalized_direction == TouchDirection.INCOMING else 'sent'}"
    if normalized_channel_code in {"documents", "proposal"}:
        return f"{normalized_channel_code}_{'received' if normalized_direction == TouchDirection.INCOMING else 'sent'}"
    return f"{normalized_channel_code}_{normalized_direction or 'outgoing'}"


class TouchResult(models.Model):
    code = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Код")
    name = models.CharField(max_length=128, unique=True, verbose_name="Результат касания")
    group = models.CharField(max_length=64, blank=True, default="", verbose_name="Группа")
    result_class = models.CharField(max_length=32, blank=True, default="", verbose_name="Класс")
    requires_next_step = models.BooleanField(default=False, verbose_name="Требует следующий шаг")
    requires_loss_reason = models.BooleanField(default=False, verbose_name="Требует причину потери")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    sort_order = models.PositiveIntegerField(default=100, verbose_name="Порядок сортировки")
    allowed_touch_types = models.JSONField(default=list, blank=True, verbose_name="Разрешенные типы касания")

    class Meta:
        verbose_name = "Результат касания"
        verbose_name_plural = "Результаты касаний"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            base_code = slugify(self.name, allow_unicode=False).replace("-", "_") or "touch_result"
            self.code = base_code[:64]
        self.allowed_touch_types = [
            normalize_touch_channel_code(item)
            for item in list(self.allowed_touch_types or [])
            if str(item or "").strip()
        ]
        super().save(*args, **kwargs)


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
    result_option = models.ForeignKey(
        "crm.TouchResult",
        related_name="touches",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Результат касания",
    )
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
    deal_documents = models.ManyToManyField(
        "crm.DealDocument",
        related_name="touches",
        blank=True,
        verbose_name="Документы сделки",
    )
    client_documents = models.ManyToManyField(
        "crm.ClientDocument",
        related_name="touches",
        blank=True,
        verbose_name="Документы компании",
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
        return self.summary or getattr(self.result_option, "name", "") or f"Касание #{self.pk}"
