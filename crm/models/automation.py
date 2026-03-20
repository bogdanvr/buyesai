from django.conf import settings
from django.db import models

from crm.models.common import TimestampedModel


class AutomationTouchpointMode(models.TextChoices):
    NONE = "none", "Не создавать"
    DRAFT = "draft", "Черновик"
    CREATE = "create", "Создать"


class AutomationUiMode(models.TextChoices):
    HISTORY_ONLY = "history_only", "Только история"
    SIGNAL = "signal", "Сигнал"
    NEEDS_ATTENTION = "needs_attention", "Требует внимания"
    DRAFT_TOUCH = "draft_touch", "Черновик касания"
    NEXT_STEP_PROMPT = "next_step_prompt", "Следующий шаг"


class AutomationUiPriority(models.TextChoices):
    LOW = "low", "Низкий"
    MEDIUM = "medium", "Средний"
    HIGH = "high", "Высокий"
    CRITICAL = "critical", "Критичный"


class NextStepTemplate(models.Model):
    code = models.CharField(max_length=64, unique=True, verbose_name="Код")
    name = models.CharField(max_length=255, unique=True, verbose_name="Название")

    class Meta:
        verbose_name = "Шаблон следующего шага"
        verbose_name_plural = "Шаблоны следующих шагов"
        ordering = ("name",)

    def __str__(self):
        return self.name


class OutcomeCatalog(models.Model):
    code = models.CharField(max_length=64, unique=True, verbose_name="Код")
    name = models.CharField(max_length=255, verbose_name="Название")

    class Meta:
        verbose_name = "Каталог результата"
        verbose_name_plural = "Каталог результатов"
        ordering = ("name",)

    def __str__(self):
        return self.name


class AutomationRule(models.Model):
    event_type = models.CharField(max_length=64, unique=True, verbose_name="Тип события")
    ui_mode = models.CharField(
        max_length=32,
        choices=AutomationUiMode.choices,
        default=AutomationUiMode.HISTORY_ONLY,
        verbose_name="UI-режим",
    )
    ui_priority = models.CharField(
        max_length=16,
        choices=AutomationUiPriority.choices,
        default=AutomationUiPriority.LOW,
        verbose_name="UI-приоритет",
    )
    write_timeline = models.BooleanField(default=True, verbose_name="Писать в ленту")
    show_in_summary = models.BooleanField(default=False, verbose_name="Показывать в summary")
    show_in_attention_queue = models.BooleanField(default=False, verbose_name="Показывать в очереди внимания")
    merge_key = models.CharField(max_length=32, blank=True, default="", verbose_name="Ключ цепочки")
    auto_open_panel = models.BooleanField(default=False, verbose_name="Автооткрывать панель")
    create_message = models.BooleanField(default=False, verbose_name="Создавать сообщение")
    create_touchpoint_mode = models.CharField(
        max_length=16,
        choices=AutomationTouchpointMode.choices,
        default=AutomationTouchpointMode.NONE,
        verbose_name="Режим создания касания",
    )
    default_outcome = models.ForeignKey(
        "crm.OutcomeCatalog",
        related_name="automation_rules",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Результат по умолчанию",
    )
    require_manager_confirmation = models.BooleanField(default=False, verbose_name="Требовать подтверждение менеджера")
    allow_auto_create_task = models.BooleanField(default=False, verbose_name="Разрешить автосоздание задачи")
    next_step_template = models.ForeignKey(
        "crm.NextStepTemplate",
        related_name="automation_rules",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Шаблон следующего шага",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    sort_order = models.PositiveIntegerField(default=100, verbose_name="Порядок сортировки")

    class Meta:
        verbose_name = "Правило автоматизации"
        verbose_name_plural = "Правила автоматизации"
        ordering = ("sort_order", "event_type")

    def __str__(self):
        return self.event_type


class AutomationDraftKind(models.TextChoices):
    TOUCH = "touch", "Черновик касания"
    NEXT_STEP = "next_step", "Черновик следующего шага"


class AutomationDraftStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    CONFIRMED = "confirmed", "Подтверждён"
    DISMISSED = "dismissed", "Отклонён"


class AutomationQueueItemKind(models.TextChoices):
    ATTENTION = "attention", "Требует внимания"
    NEXT_STEP = "next_step", "Следующее действие"


class AutomationQueueItemStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    RESOLVED = "resolved", "Обработан"
    DISMISSED = "dismissed", "Отклонён"


class AutomationMessageDraftStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    CONFIRMED = "confirmed", "Подтверждён"
    DISMISSED = "dismissed", "Отклонён"


class AutomationOutboundMessageStatus(models.TextChoices):
    SENT = "sent", "Отправлено"
    MANUAL_REQUIRED = "manual_required", "Нужна ручная отправка"
    FAILED = "failed", "Ошибка отправки"


class AutomationDraft(TimestampedModel):
    automation_rule = models.ForeignKey(
        "crm.AutomationRule",
        related_name="drafts",
        on_delete=models.CASCADE,
        verbose_name="Правило автоматизации",
    )
    source_touch = models.ForeignKey(
        "crm.Touch",
        related_name="automation_drafts",
        on_delete=models.CASCADE,
        verbose_name="Исходное касание",
    )
    draft_kind = models.CharField(
        max_length=16,
        choices=AutomationDraftKind.choices,
        default=AutomationDraftKind.TOUCH,
        verbose_name="Тип черновика",
    )
    status = models.CharField(
        max_length=16,
        choices=AutomationDraftStatus.choices,
        default=AutomationDraftStatus.PENDING,
        verbose_name="Статус",
    )
    source_event_type = models.CharField(max_length=64, blank=True, default="", verbose_name="Тип исходного события")
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="Заголовок")
    summary = models.TextField(blank=True, default="", verbose_name="Описание")
    outcome = models.ForeignKey(
        "crm.OutcomeCatalog",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Каталог результата",
    )
    touch_result = models.ForeignKey(
        "crm.TouchResult",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Результат касания",
    )
    next_step_template = models.ForeignKey(
        "crm.NextStepTemplate",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Шаблон следующего шага",
    )
    proposed_channel = models.ForeignKey(
        "crm.CommunicationChannel",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Предложенный канал",
    )
    proposed_direction = models.CharField(max_length=16, blank=True, default="", verbose_name="Предложенное направление")
    proposed_next_step = models.TextField(blank=True, default="", verbose_name="Предложенный следующий шаг")
    proposed_next_step_at = models.DateTimeField(blank=True, null=True, verbose_name="Предложенная дата следующего шага")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Лид",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    task = models.ForeignKey(
        "crm.Activity",
        related_name="automation_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Задача",
    )
    acted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_automation_drafts_acted",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Обработал",
    )
    acted_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда обработан")

    class Meta:
        verbose_name = "Черновик автоматизации"
        verbose_name_plural = "Черновики автоматизации"
        ordering = ("status", "-created_at", "-id")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["draft_kind"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["client"]),
            models.Index(fields=["lead"]),
            models.Index(fields=["source_touch"]),
        ]

    def __str__(self):
        return self.title or f"Черновик #{self.pk}"


class AutomationQueueItem(TimestampedModel):
    automation_rule = models.ForeignKey(
        "crm.AutomationRule",
        related_name="queue_items",
        on_delete=models.CASCADE,
        verbose_name="Правило автоматизации",
    )
    source_touch = models.ForeignKey(
        "crm.Touch",
        related_name="automation_queue_items",
        on_delete=models.CASCADE,
        verbose_name="Исходное касание",
    )
    item_kind = models.CharField(
        max_length=16,
        choices=AutomationQueueItemKind.choices,
        default=AutomationQueueItemKind.ATTENTION,
        verbose_name="Тип элемента",
    )
    status = models.CharField(
        max_length=16,
        choices=AutomationQueueItemStatus.choices,
        default=AutomationQueueItemStatus.PENDING,
        verbose_name="Статус",
    )
    source_event_type = models.CharField(max_length=64, blank=True, default="", verbose_name="Тип исходного события")
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="Заголовок")
    summary = models.TextField(blank=True, default="", verbose_name="Описание")
    recommended_action = models.TextField(blank=True, default="", verbose_name="Рекомендованное действие")
    outcome = models.ForeignKey(
        "crm.OutcomeCatalog",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Каталог результата",
    )
    touch_result = models.ForeignKey(
        "crm.TouchResult",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Результат касания",
    )
    next_step_template = models.ForeignKey(
        "crm.NextStepTemplate",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Шаблон следующего шага",
    )
    proposed_channel = models.ForeignKey(
        "crm.CommunicationChannel",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Предложенный канал",
    )
    proposed_direction = models.CharField(max_length=16, blank=True, default="", verbose_name="Предложенное направление")
    proposed_next_step = models.TextField(blank=True, default="", verbose_name="Предложенный следующий шаг")
    proposed_next_step_at = models.DateTimeField(blank=True, null=True, verbose_name="Предложенная дата следующего шага")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Лид",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    task = models.ForeignKey(
        "crm.Activity",
        related_name="automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Связанная задача",
    )
    created_task = models.ForeignKey(
        "crm.Activity",
        related_name="created_from_automation_queue_items",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Созданная задача",
    )
    acted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_automation_queue_items_acted",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Обработал",
    )
    acted_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда обработан")

    class Meta:
        verbose_name = "Элемент очереди автоматизации"
        verbose_name_plural = "Очередь автоматизации"
        ordering = ("status", "-created_at", "-id")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["item_kind"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["client"]),
            models.Index(fields=["lead"]),
            models.Index(fields=["source_touch"]),
        ]

    def __str__(self):
        return self.title or f"Очередь #{self.pk}"


class AutomationMessageDraft(TimestampedModel):
    automation_rule = models.ForeignKey(
        "crm.AutomationRule",
        related_name="message_drafts",
        on_delete=models.CASCADE,
        verbose_name="Правило автоматизации",
    )
    source_touch = models.ForeignKey(
        "crm.Touch",
        related_name="automation_message_drafts",
        on_delete=models.CASCADE,
        verbose_name="Исходное касание",
    )
    status = models.CharField(
        max_length=16,
        choices=AutomationMessageDraftStatus.choices,
        default=AutomationMessageDraftStatus.PENDING,
        verbose_name="Статус",
    )
    source_event_type = models.CharField(max_length=64, blank=True, default="", verbose_name="Тип исходного события")
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="Заголовок")
    message_subject = models.CharField(max_length=255, blank=True, default="", verbose_name="Тема сообщения")
    message_text = models.TextField(blank=True, default="", verbose_name="Текст сообщения")
    proposed_channel = models.ForeignKey(
        "crm.CommunicationChannel",
        related_name="automation_message_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Канал сообщения",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_automation_message_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        related_name="automation_message_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Лид",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="automation_message_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="automation_message_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="automation_message_drafts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    acted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_automation_message_drafts_acted",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Обработал",
    )
    acted_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда обработан")

    class Meta:
        verbose_name = "Черновик сообщения автоматизации"
        verbose_name_plural = "Черновики сообщений автоматизации"
        ordering = ("status", "-created_at", "-id")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["client"]),
            models.Index(fields=["lead"]),
            models.Index(fields=["source_touch"]),
        ]

    def __str__(self):
        return self.title or f"Черновик сообщения #{self.pk}"


class AutomationOutboundMessage(TimestampedModel):
    automation_rule = models.ForeignKey(
        "crm.AutomationRule",
        related_name="outbound_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Правило автоматизации",
    )
    message_draft = models.ForeignKey(
        "crm.AutomationMessageDraft",
        related_name="outbound_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Черновик сообщения",
    )
    source_touch = models.ForeignKey(
        "crm.Touch",
        related_name="automation_outbound_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Исходное касание",
    )
    source_event_type = models.CharField(max_length=64, blank=True, default="", verbose_name="Тип исходного события")
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="Заголовок")
    message_subject = models.CharField(max_length=255, blank=True, default="", verbose_name="Тема сообщения")
    message_text = models.TextField(blank=True, default="", verbose_name="Текст сообщения")
    channel_code = models.CharField(max_length=32, blank=True, default="", verbose_name="Код канала")
    provider = models.CharField(max_length=32, blank=True, default="", verbose_name="Провайдер")
    recipient = models.CharField(max_length=255, blank=True, default="", verbose_name="Получатель")
    recipient_display = models.CharField(max_length=255, blank=True, default="", verbose_name="Отображение получателя")
    status = models.CharField(
        max_length=32,
        choices=AutomationOutboundMessageStatus.choices,
        default=AutomationOutboundMessageStatus.FAILED,
        verbose_name="Статус отправки",
    )
    external_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Внешний ID")
    provider_response = models.JSONField(default=dict, blank=True, verbose_name="Ответ провайдера")
    error_message = models.TextField(blank=True, default="", verbose_name="Ошибка")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_automation_outbound_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        related_name="automation_outbound_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Лид",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="automation_outbound_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="automation_outbound_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="automation_outbound_messages",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    acted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_automation_outbound_messages_acted",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Подтвердил отправку",
    )
    acted_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда подтверждено")
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name="Когда отправлено")

    class Meta:
        verbose_name = "Исходящее сообщение автоматизации"
        verbose_name_plural = "Исходящие сообщения автоматизации"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["channel_code"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["client"]),
            models.Index(fields=["lead"]),
            models.Index(fields=["message_draft"]),
            models.Index(fields=["source_touch"]),
        ]

    def __str__(self):
        return self.title or f"Исходящее сообщение #{self.pk}"
