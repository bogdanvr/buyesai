from pathlib import Path
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from crm.models.common import TimestampedModel


def truncate_attachment_filename(filename: str, max_stem_length: int = 120) -> str:
    safe_name = Path(str(filename or "attachment")).name or "attachment"
    path = Path(safe_name)
    suffix = path.suffix or ""
    stem = path.stem or "attachment"
    if len(stem) <= max_stem_length:
        return f"{stem}{suffix}"
    return f"{stem[:max_stem_length]}{suffix}"


def message_attachment_upload_to(instance, filename: str) -> str:
    message_id = getattr(instance, "message_id", None) or getattr(getattr(instance, "message", None), "id", None) or "new"
    safe_name = truncate_attachment_filename(filename)
    return f"communications/message_{message_id}/{safe_name}"


def generate_share_token() -> str:
    return uuid.uuid4().hex


class CommunicationChannelCode(models.TextChoices):
    EMAIL = "email", "Email"
    TELEGRAM = "telegram", "Telegram"


class ConversationStatus(models.TextChoices):
    ACTIVE = "active", "Активный"
    ARCHIVED = "archived", "В архиве"
    CLOSED = "closed", "Закрыт"


class MessageDirection(models.TextChoices):
    INCOMING = "incoming", "Входящее"
    OUTGOING = "outgoing", "Исходящее"


class MessageType(models.TextChoices):
    TEXT = "text", "Текст"
    EMAIL = "email", "Письмо"
    SERVICE = "service", "Служебное"


class MessageStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    QUEUED = "queued", "В очереди"
    SENDING = "sending", "Отправляется"
    SENT = "sent", "Отправлено"
    DELIVERED = "delivered", "Доставлено"
    RECEIVED = "received", "Получено"
    FAILED = "failed", "Ошибка"
    REQUIRES_MANUAL_RETRY = "requires_manual_retry", "Требует ручного повтора"


class AttemptStatus(models.TextChoices):
    STARTED = "started", "Запущена"
    SUCCEEDED = "succeeded", "Успешно"
    FAILED = "failed", "Ошибка"
    RETRY_SCHEDULED = "retry_scheduled", "Повтор запланирован"


class ErrorClass(models.TextChoices):
    TEMPORARY = "temporary", "Временная"
    PERMANENT = "permanent", "Постоянная"
    VALIDATION = "validation", "Ошибка валидации"
    MANUAL_REQUIRED = "manual_required", "Нужно ручное действие"


class WebhookProcessingStatus(models.TextChoices):
    PENDING = "pending", "Ожидает обработки"
    PROCESSED = "processed", "Обработано"
    FAILED = "failed", "Ошибка"
    IGNORED = "ignored", "Игнорировано"


class DeliveryFailureResolutionStatus(models.TextChoices):
    OPEN = "open", "Открыта"
    IN_PROGRESS = "in_progress", "В работе"
    RESOLVED = "resolved", "Решена"
    CLOSED = "closed", "Закрыта"


class DealDocumentShareEventType(models.TextChoices):
    EMAIL_SENT = "email_sent", "Письмо отправлено"
    EMAIL_FAILED = "email_failed", "Ошибка отправки письма"
    DOCUMENT_OPENED = "document_opened", "Документ открыт"
    PAGE_OPENED = "page_opened", "Страница документа открыта"
    PAGE_VIEWED = "page_viewed", "Страница PDF просмотрена"
    LAST_PAGE_REACHED = "last_page_reached", "Последняя страница достигнута"
    PDF_DOWNLOADED = "pdf_downloaded", "PDF документа скачан"
    VIEWER_CLOSED = "viewer_closed", "Viewer закрыт"
    TIME_IN_VIEWER = "time_in_viewer", "Время в viewer"


class Conversation(TimestampedModel):
    channel = models.CharField(
        max_length=32,
        choices=CommunicationChannelCode.choices,
        verbose_name="Канал",
    )
    subject = models.CharField(max_length=255, blank=True, default="", verbose_name="Тема диалога")
    client = models.ForeignKey(
        "crm.Client",
        related_name="conversations",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="conversations",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="conversations",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    status = models.CharField(
        max_length=32,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
        verbose_name="Статус диалога",
    )
    requires_manual_binding = models.BooleanField(default=False, verbose_name="Требует ручной привязки")
    last_message = models.ForeignKey(
        "crm_communications.Message",
        related_name="conversation_last_for",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Последнее сообщение",
    )
    last_message_direction = models.CharField(
        max_length=16,
        choices=MessageDirection.choices,
        blank=True,
        default="",
        verbose_name="Направление последнего сообщения",
    )
    last_message_preview = models.CharField(max_length=500, blank=True, default="", verbose_name="Превью последнего сообщения")
    last_message_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата последнего сообщения")
    last_incoming_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата последнего входящего")
    last_outgoing_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата последнего исходящего")

    class Meta:
        verbose_name = "Диалог"
        verbose_name_plural = "Диалоги"
        ordering = ("-last_message_at", "-id")
        indexes = [
            models.Index(fields=["channel"]),
            models.Index(fields=["client"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["last_message_at"]),
            models.Index(fields=["requires_manual_binding"]),
        ]

    def __str__(self):
        return self.subject or f"Диалог #{self.pk}"


class ConversationRoute(TimestampedModel):
    conversation = models.ForeignKey(
        "crm_communications.Conversation",
        related_name="routes",
        on_delete=models.CASCADE,
        verbose_name="Диалог",
    )
    channel = models.CharField(
        max_length=32,
        choices=CommunicationChannelCode.choices,
        verbose_name="Канал",
    )
    route_type = models.CharField(max_length=64, verbose_name="Тип маршрута")
    route_key = models.CharField(max_length=255, verbose_name="Ключ маршрута")
    client = models.ForeignKey(
        "crm.Client",
        related_name="conversation_routes",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="conversation_routes",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="conversation_routes",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    is_primary = models.BooleanField(default=False, verbose_name="Основной маршрут")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="resolved_conversation_routes",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Кто привязал",
    )
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда привязали")
    resolution_source = models.CharField(max_length=64, blank=True, default="", verbose_name="Источник привязки")

    class Meta:
        verbose_name = "Маршрут диалога"
        verbose_name_plural = "Маршруты диалогов"
        ordering = ("-is_primary", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "route_type", "route_key"],
                name="crm_comm_route_unique_channel_type_key",
            ),
        ]
        indexes = [
            models.Index(fields=["deal"]),
            models.Index(fields=["client"]),
            models.Index(fields=["is_primary"]),
        ]

    def __str__(self):
        return f"{self.channel}:{self.route_type}:{self.route_key}"


class ParticipantBinding(TimestampedModel):
    channel = models.CharField(
        max_length=32,
        choices=CommunicationChannelCode.choices,
        verbose_name="Канал",
    )
    external_participant_key = models.CharField(max_length=255, verbose_name="Внешний ключ участника")
    external_display_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Внешнее имя")
    client = models.ForeignKey(
        "crm.Client",
        related_name="participant_bindings",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="participant_bindings",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    is_primary = models.BooleanField(default=False, verbose_name="Основной binding")
    last_seen_at = models.DateTimeField(blank=True, null=True, verbose_name="Последнее появление")

    class Meta:
        verbose_name = "Привязка участника"
        verbose_name_plural = "Привязки участников"
        ordering = ("channel", "external_participant_key")
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "external_participant_key"],
                name="crm_comm_participant_unique_channel_key",
            ),
        ]
        indexes = [
            models.Index(fields=["client"]),
            models.Index(fields=["contact"]),
        ]

    def __str__(self):
        return self.external_display_name or self.external_participant_key


class Message(TimestampedModel):
    conversation = models.ForeignKey(
        "crm_communications.Conversation",
        related_name="messages",
        on_delete=models.CASCADE,
        verbose_name="Диалог",
    )
    channel = models.CharField(
        max_length=32,
        choices=CommunicationChannelCode.choices,
        verbose_name="Канал",
    )
    direction = models.CharField(
        max_length=16,
        choices=MessageDirection.choices,
        verbose_name="Направление",
    )
    message_type = models.CharField(
        max_length=32,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        verbose_name="Тип сообщения",
    )
    status = models.CharField(
        max_length=32,
        choices=MessageStatus.choices,
        default=MessageStatus.DRAFT,
        verbose_name="Статус сообщения",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="communication_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="communication_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="communication_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    touch = models.OneToOneField(
        "crm.Touch",
        related_name="communication_message",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Связанное касание",
    )
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="communication_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Автор в CRM",
    )
    external_sender_key = models.CharField(max_length=255, blank=True, default="", verbose_name="Внешний отправитель")
    external_recipient_key = models.CharField(max_length=255, blank=True, default="", verbose_name="Внешний получатель")
    subject = models.CharField(max_length=255, blank=True, default="", verbose_name="Тема")
    body_text = models.TextField(blank=True, default="", verbose_name="Текст")
    body_html = models.TextField(blank=True, default="", verbose_name="HTML")
    body_preview = models.CharField(max_length=500, blank=True, default="", verbose_name="Превью")
    provider_message_id = models.CharField(max_length=255, blank=True, default="", verbose_name="ID сообщения у провайдера")
    provider_chat_id = models.CharField(max_length=255, blank=True, default="", verbose_name="ID чата у провайдера")
    provider_thread_key = models.CharField(max_length=255, blank=True, default="", verbose_name="Ключ thread у провайдера")
    external_message_id = models.CharField(max_length=255, blank=True, default="", verbose_name="Внешний ID сообщения")
    in_reply_to = models.CharField(max_length=255, blank=True, default="", verbose_name="In-Reply-To")
    references = models.TextField(blank=True, default="", verbose_name="References")
    queued_at = models.DateTimeField(blank=True, null=True, verbose_name="Поставлено в очередь")
    next_attempt_at = models.DateTimeField(blank=True, null=True, verbose_name="Следующая попытка не раньше")
    sending_started_at = models.DateTimeField(blank=True, null=True, verbose_name="Начало отправки")
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name="Отправлено")
    received_at = models.DateTimeField(blank=True, null=True, verbose_name="Получено")
    delivered_at = models.DateTimeField(blank=True, null=True, verbose_name="Доставлено")
    failed_at = models.DateTimeField(blank=True, null=True, verbose_name="Ошибка")
    retry_count = models.PositiveSmallIntegerField(default=0, verbose_name="Количество повторов")
    last_error_code = models.CharField(max_length=128, blank=True, default="", verbose_name="Последний код ошибки")
    last_error_message = models.TextField(blank=True, default="", verbose_name="Последняя ошибка")
    requires_manual_retry = models.BooleanField(default=False, verbose_name="Требует ручного повтора")

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "external_message_id"],
                condition=~Q(external_message_id=""),
                name="crm_comm_message_unique_channel_external_message_id",
            ),
        ]
        indexes = [
            models.Index(fields=["conversation"]),
            models.Index(fields=["channel"]),
            models.Index(fields=["direction"]),
            models.Index(fields=["status"]),
            models.Index(fields=["client"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["provider_message_id"]),
            models.Index(fields=["next_attempt_at"]),
        ]

    def __str__(self):
        return self.subject or self.body_preview or f"Сообщение #{self.pk}"


class MessageAttachment(TimestampedModel):
    message = models.ForeignKey(
        "crm_communications.Message",
        related_name="attachments",
        on_delete=models.CASCADE,
        verbose_name="Сообщение",
    )
    file = models.FileField(upload_to=message_attachment_upload_to, max_length=500, verbose_name="Файл")
    original_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Оригинальное имя")
    mime_type = models.CharField(max_length=255, blank=True, default="", verbose_name="MIME type")
    size_bytes = models.BigIntegerField(default=0, verbose_name="Размер в байтах")
    content_id = models.CharField(max_length=255, blank=True, default="", verbose_name="Content-ID")
    is_inline = models.BooleanField(default=False, verbose_name="Inline")
    provider_attachment_id = models.CharField(max_length=255, blank=True, default="", verbose_name="ID вложения у провайдера")

    class Meta:
        verbose_name = "Вложение сообщения"
        verbose_name_plural = "Вложения сообщений"
        ordering = ("id",)

    def __str__(self):
        return self.original_name or self.file.name.rsplit("/", 1)[-1] or f"Вложение #{self.pk}"


class DealDocumentShare(TimestampedModel):
    document = models.ForeignKey(
        "crm.DealDocument",
        related_name="shares",
        on_delete=models.CASCADE,
        verbose_name="Документ сделки",
    )
    message = models.ForeignKey(
        "crm_communications.Message",
        related_name="deal_document_shares",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сообщение",
    )
    channel = models.CharField(
        max_length=32,
        choices=CommunicationChannelCode.choices,
        default=CommunicationChannelCode.EMAIL,
        verbose_name="Канал",
    )
    recipient = models.CharField(max_length=255, blank=True, default="", verbose_name="Получатель")
    token = models.CharField(max_length=32, unique=True, db_index=True, default=generate_share_token, verbose_name="Публичный токен")
    first_opened_at = models.DateTimeField(blank=True, null=True, verbose_name="Первое открытие страницы")
    last_opened_at = models.DateTimeField(blank=True, null=True, verbose_name="Последнее открытие страницы")
    last_downloaded_at = models.DateTimeField(blank=True, null=True, verbose_name="Последнее скачивание PDF")
    open_count = models.PositiveIntegerField(default=0, verbose_name="Количество открытий страницы")
    download_count = models.PositiveIntegerField(default=0, verbose_name="Количество скачиваний PDF")
    first_open_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP первого открытия")
    last_open_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP последнего открытия")
    first_open_user_agent = models.TextField(blank=True, default="", verbose_name="User-Agent первого открытия")
    last_open_user_agent = models.TextField(blank=True, default="", verbose_name="User-Agent последнего открытия")

    class Meta:
        verbose_name = "Публичная отправка документа сделки"
        verbose_name_plural = "Публичные отправки документов сделки"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["document"]),
            models.Index(fields=["message"]),
            models.Index(fields=["channel"]),
            models.Index(fields=["last_opened_at"]),
        ]

    def __str__(self):
        return f"Share #{self.pk} for document #{self.document_id}"


class DealDocumentShareEvent(TimestampedModel):
    share = models.ForeignKey(
        "crm_communications.DealDocumentShare",
        related_name="events",
        on_delete=models.CASCADE,
        verbose_name="Публичная отправка",
    )
    message = models.ForeignKey(
        "crm_communications.Message",
        related_name="deal_document_share_events",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сообщение",
    )
    event_type = models.CharField(
        max_length=32,
        choices=DealDocumentShareEventType.choices,
        verbose_name="Тип события",
    )
    happened_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name="Когда произошло")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP")
    user_agent = models.TextField(blank=True, default="", verbose_name="User-Agent")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Метаданные")

    class Meta:
        verbose_name = "Событие публичной отправки документа"
        verbose_name_plural = "События публичных отправок документов"
        ordering = ("-happened_at", "-id")
        indexes = [
            models.Index(fields=["share"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["message"]),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} #{self.pk}"


class MessageAttemptLog(TimestampedModel):
    message = models.ForeignKey(
        "crm_communications.Message",
        related_name="attempt_logs",
        on_delete=models.CASCADE,
        verbose_name="Сообщение",
    )
    attempt_number = models.PositiveSmallIntegerField(verbose_name="Номер попытки")
    transport = models.CharField(
        max_length=32,
        choices=CommunicationChannelCode.choices,
        verbose_name="Транспорт",
    )
    started_at = models.DateTimeField(blank=True, null=True, verbose_name="Начало попытки")
    finished_at = models.DateTimeField(blank=True, null=True, verbose_name="Окончание попытки")
    status = models.CharField(
        max_length=32,
        choices=AttemptStatus.choices,
        verbose_name="Статус попытки",
    )
    error_class = models.CharField(
        max_length=32,
        choices=ErrorClass.choices,
        blank=True,
        default="",
        verbose_name="Класс ошибки",
    )
    error_code = models.CharField(max_length=128, blank=True, default="", verbose_name="Код ошибки")
    error_message = models.TextField(blank=True, default="", verbose_name="Текст ошибки")
    provider_response_payload = models.JSONField(default=dict, blank=True, verbose_name="Ответ провайдера")
    scheduled_retry_at = models.DateTimeField(blank=True, null=True, verbose_name="Повтор запланирован на")
    is_final = models.BooleanField(default=False, verbose_name="Финальная попытка")

    class Meta:
        verbose_name = "Лог попытки отправки"
        verbose_name_plural = "Логи попыток отправки"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["message"]),
            models.Index(fields=["attempt_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["scheduled_retry_at"]),
        ]

    def __str__(self):
        return f"Попытка #{self.attempt_number} для сообщения #{self.message_id}"


class MessageWebhookEvent(TimestampedModel):
    channel = models.CharField(
        max_length=32,
        choices=CommunicationChannelCode.choices,
        verbose_name="Канал",
    )
    event_type = models.CharField(max_length=64, verbose_name="Тип события")
    external_event_id = models.CharField(max_length=255, blank=True, default="", verbose_name="Внешний ID события")
    external_message_id = models.CharField(max_length=255, blank=True, default="", verbose_name="Внешний ID сообщения")
    payload = models.JSONField(default=dict, blank=True, verbose_name="Payload")
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда обработано")
    processing_status = models.CharField(
        max_length=32,
        choices=WebhookProcessingStatus.choices,
        default=WebhookProcessingStatus.PENDING,
        verbose_name="Статус обработки",
    )
    error_message = models.TextField(blank=True, default="", verbose_name="Ошибка обработки")

    class Meta:
        verbose_name = "Webhook событие сообщения"
        verbose_name_plural = "Webhook события сообщений"
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "external_event_id"],
                condition=~Q(external_event_id=""),
                name="crm_comm_webhook_unique_channel_external_event_id",
            ),
        ]
        indexes = [
            models.Index(fields=["external_message_id"]),
            models.Index(fields=["processing_status"]),
        ]

    def __str__(self):
        return f"{self.channel}:{self.event_type}:{self.external_event_id or self.pk}"


class DeliveryFailureQueue(TimestampedModel):
    message = models.OneToOneField(
        "crm_communications.Message",
        related_name="delivery_failure_queue_item",
        on_delete=models.CASCADE,
        verbose_name="Сообщение",
    )
    failure_type = models.CharField(max_length=64, verbose_name="Тип сбоя")
    opened_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда попало в очередь")
    last_attempt_log = models.ForeignKey(
        "crm_communications.MessageAttemptLog",
        related_name="failure_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Последняя попытка",
    )
    resolution_status = models.CharField(
        max_length=32,
        choices=DeliveryFailureResolutionStatus.choices,
        default=DeliveryFailureResolutionStatus.OPEN,
        verbose_name="Статус обработки",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="delivery_failure_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Назначено на",
    )
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда решено")
    resolution_comment = models.TextField(blank=True, default="", verbose_name="Комментарий по решению")

    class Meta:
        verbose_name = "Очередь ошибок доставки"
        verbose_name_plural = "Очередь ошибок доставки"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["resolution_status"]),
            models.Index(fields=["assigned_to"]),
        ]

    def __str__(self):
        return f"Ошибка доставки для сообщения #{self.message_id}"
