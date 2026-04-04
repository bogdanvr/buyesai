from django.db import models
from django.conf import settings

from crm.models.common import TimestampedModel


class IntegrationWebhookEvent(models.Model):
    source = models.CharField(max_length=64, verbose_name="Источник")
    event_type = models.CharField(max_length=128, verbose_name="Тип события")
    external_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Внешний ID")
    payload = models.JSONField(default=dict, blank=True, verbose_name="Payload")
    is_processed = models.BooleanField(default=False, verbose_name="Обработано")
    process_error = models.TextField(blank=True, default="", verbose_name="Ошибка обработки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="Обработано в")

    class Meta:
        verbose_name = "Webhook событие"
        verbose_name_plural = "Webhook события"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["is_processed"]),
        ]

    def __str__(self):
        return f"{self.source}:{self.event_type}"


class UserIntegrationProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="integration_profile",
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )
    phone = models.CharField(max_length=64, blank=True, default="", verbose_name="Телефон")
    email = models.EmailField(blank=True, default="", verbose_name="Email для уведомлений")
    telegram_chat_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Telegram chat ID",
        help_text="Личный chat_id, куда бот будет отправлять уведомления",
    )

    class Meta:
        verbose_name = "Интеграционный профиль пользователя"
        verbose_name_plural = "Интеграционные профили пользователей"

    def __str__(self):
        username = getattr(self.user, "username", "") or f"user-{self.user_id}"
        return f"Профиль интеграций: {username}"


class TelephonyProvider(models.TextChoices):
    NOVOFON = "novofon", "Novofon"


class LlmProvider(models.TextChoices):
    OPENAI = "openai", "OpenAI"
    DEEPSEEK = "deepseek", "DeepSeek"
    YANDEXGPT = "yandexgpt", "YandexGPT"
    CUSTOM = "custom", "Свой провайдер"


class LlmApiStyle(models.TextChoices):
    OPENAI_COMPATIBLE = "openai_compatible", "OpenAI-совместимый API"


class PhoneCallDirection(models.TextChoices):
    INBOUND = "inbound", "Входящий"
    OUTBOUND = "outbound", "Исходящий"


class PhoneCallStatus(models.TextChoices):
    RINGING = "ringing", "Звонит"
    ANSWERED = "answered", "Отвечен"
    MISSED = "missed", "Пропущен"
    COMPLETED = "completed", "Завершен"
    FAILED = "failed", "Ошибка"
    CANCELED = "canceled", "Отменен"


class PhoneCallTranscriptionStatus(models.TextChoices):
    NOT_REQUESTED = "not_requested", "Не запрошена"
    QUEUED = "queued", "В очереди"
    PROCESSING = "processing", "Обрабатывается"
    COMPLETED = "completed", "Готово"
    FAILED = "failed", "Ошибка"


class TelephonyEventStatus(models.TextChoices):
    RECEIVED = "received", "Получено"
    QUEUED = "queued", "В очереди"
    PROCESSING = "processing", "Обрабатывается"
    PROCESSED = "processed", "Обработано"
    FAILED = "failed", "Ошибка"
    IGNORED_DUPLICATE = "ignored_duplicate", "Дубликат"


class TelephonyProviderAccount(TimestampedModel):
    provider = models.CharField(
        max_length=32,
        choices=TelephonyProvider.choices,
        unique=True,
        verbose_name="Провайдер",
    )
    enabled = models.BooleanField(default=False, verbose_name="Интеграция включена")
    api_key = models.CharField(max_length=255, blank=True, default="", verbose_name="API key")
    api_secret = models.CharField(max_length=255, blank=True, default="", verbose_name="API secret")
    api_base_url = models.CharField(max_length=500, blank=True, default="", verbose_name="Базовый URL API")
    webhook_path = models.CharField(max_length=255, blank=True, default="/api/integrations/novofon/webhook/", verbose_name="Путь webhook")
    default_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="default_telephony_provider_accounts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный по умолчанию",
    )
    create_lead_for_unknown_number = models.BooleanField(default=False, verbose_name="Создавать лид для неизвестного номера")
    create_task_for_missed_call = models.BooleanField(default=False, verbose_name="Создавать задачу по пропущенному звонку")
    link_calls_to_open_deal_only = models.BooleanField(default=True, verbose_name="Привязывать звонки только к открытой сделке")
    allowed_virtual_numbers = models.JSONField(default=list, blank=True, verbose_name="Разрешенные виртуальные номера")
    is_debug_logging_enabled = models.BooleanField(default=False, verbose_name="Расширенное логирование")
    webhook_shared_secret = models.CharField(max_length=255, blank=True, default="", verbose_name="Секрет webhook")
    settings_json = models.JSONField(default=dict, blank=True, verbose_name="Дополнительные настройки")
    last_connection_checked_at = models.DateTimeField(blank=True, null=True, verbose_name="Последняя проверка подключения")
    last_connection_status = models.CharField(max_length=32, blank=True, default="", verbose_name="Статус последней проверки")
    last_connection_error = models.TextField(blank=True, default="", verbose_name="Ошибка последней проверки")

    class Meta:
        verbose_name = "Аккаунт телефонии"
        verbose_name_plural = "Аккаунты телефонии"
        ordering = ("provider",)

    def __str__(self):
        return self.get_provider_display()


class TelephonyUserMapping(TimestampedModel):
    provider_account = models.ForeignKey(
        TelephonyProviderAccount,
        related_name="user_mappings",
        on_delete=models.CASCADE,
        verbose_name="Аккаунт провайдера",
    )
    crm_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="telephony_user_mappings",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Пользователь CRM",
    )
    novofon_employee_id = models.CharField(max_length=128, verbose_name="ID сотрудника Novofon")
    novofon_extension = models.CharField(max_length=64, blank=True, default="", verbose_name="Внутренний номер")
    novofon_full_name = models.CharField(max_length=255, blank=True, default="", verbose_name="ФИО в Novofon")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_default_owner = models.BooleanField(default=False, verbose_name="Ответственный по умолчанию")
    external_payload = models.JSONField(default=dict, blank=True, verbose_name="Данные сотрудника")

    class Meta:
        verbose_name = "Сопоставление пользователя телефонии"
        verbose_name_plural = "Сопоставления пользователей телефонии"
        ordering = ("novofon_full_name", "novofon_extension", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["provider_account", "novofon_employee_id"],
                name="integrations_unique_provider_employee_mapping",
            ),
            models.UniqueConstraint(
                fields=["provider_account", "crm_user"],
                condition=models.Q(crm_user__isnull=False),
                name="integrations_unique_provider_crm_user_mapping",
            ),
        ]
        indexes = [
            models.Index(fields=["novofon_extension"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        crm_user = getattr(self.crm_user, "username", "") or "unassigned"
        return f"{self.novofon_full_name or self.novofon_employee_id} -> {crm_user}"


class LlmProviderAccount(TimestampedModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="Название")
    provider = models.CharField(
        max_length=32,
        choices=LlmProvider.choices,
        default=LlmProvider.CUSTOM,
        verbose_name="Провайдер",
    )
    api_style = models.CharField(
        max_length=32,
        choices=LlmApiStyle.choices,
        default=LlmApiStyle.OPENAI_COMPATIBLE,
        verbose_name="Стиль API",
    )
    base_url = models.CharField(max_length=500, blank=True, default="", verbose_name="Базовый URL API")
    model = models.CharField(max_length=255, blank=True, default="", verbose_name="Модель")
    api_key_encrypted = models.TextField(blank=True, default="", verbose_name="API key (зашифрованный)")
    api_key_last4 = models.CharField(max_length=16, blank=True, default="", verbose_name="Последние символы API key")
    organization = models.CharField(max_length=255, blank=True, default="", verbose_name="Organization")
    project = models.CharField(max_length=255, blank=True, default="", verbose_name="Project")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    use_for_touch_analysis = models.BooleanField(default=False, verbose_name="Использовать для анализа касаний")
    priority = models.PositiveIntegerField(default=100, verbose_name="Приоритет")

    class Meta:
        verbose_name = "LLM провайдер"
        verbose_name_plural = "LLM провайдеры"
        ordering = ("priority", "name", "id")
        indexes = [
            models.Index(fields=["is_active", "use_for_touch_analysis", "priority"]),
            models.Index(fields=["provider"]),
        ]

    def __str__(self):
        return self.name

    @property
    def has_api_key(self) -> bool:
        return bool(str(self.api_key_encrypted or "").strip())

    @property
    def api_key_masked(self) -> str:
        if not self.has_api_key:
            return ""
        suffix = str(self.api_key_last4 or "").strip()
        return f"****{suffix}" if suffix else "Сохранён"

    def set_api_key(self, raw_value: str) -> None:
        from integrations.services.secrets import encrypt_secret

        normalized = str(raw_value or "").strip()
        if not normalized:
            self.api_key_encrypted = ""
            self.api_key_last4 = ""
            return
        self.api_key_encrypted = encrypt_secret(normalized)
        self.api_key_last4 = normalized[-4:]

    def clear_api_key(self) -> None:
        self.api_key_encrypted = ""
        self.api_key_last4 = ""

    def get_api_key(self) -> str:
        from integrations.services.secrets import decrypt_secret

        if not self.has_api_key:
            return ""
        return decrypt_secret(self.api_key_encrypted)


class PhoneCall(TimestampedModel):
    provider = models.CharField(max_length=32, choices=TelephonyProvider.choices, verbose_name="Провайдер")
    external_call_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Внешний ID звонка")
    external_parent_event_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Внешний ID события")
    direction = models.CharField(max_length=16, choices=PhoneCallDirection.choices, default=PhoneCallDirection.INBOUND, verbose_name="Направление")
    status = models.CharField(max_length=16, choices=PhoneCallStatus.choices, default=PhoneCallStatus.RINGING, verbose_name="Статус")
    phone_from = models.CharField(max_length=64, blank=True, default="", verbose_name="Номер from")
    phone_to = models.CharField(max_length=64, blank=True, default="", verbose_name="Номер to")
    client_phone_normalized = models.CharField(max_length=16, blank=True, default="", verbose_name="Номер клиента (нормализованный)")
    virtual_number = models.CharField(max_length=64, blank=True, default="", verbose_name="Виртуальный номер")
    crm_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="phone_calls",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Пользователь CRM",
    )
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="responsible_phone_calls",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="phone_calls",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    company = models.ForeignKey(
        "crm.Client",
        related_name="phone_calls",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Компания",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        related_name="phone_calls",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Лид",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="phone_calls",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    touch = models.OneToOneField(
        "crm.Touch",
        related_name="phone_call",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Касание",
    )
    started_at = models.DateTimeField(blank=True, null=True, verbose_name="Начало")
    answered_at = models.DateTimeField(blank=True, null=True, verbose_name="Ответ")
    ended_at = models.DateTimeField(blank=True, null=True, verbose_name="Окончание")
    duration_sec = models.PositiveIntegerField(blank=True, null=True, verbose_name="Длительность")
    talk_duration_sec = models.PositiveIntegerField(blank=True, null=True, verbose_name="Длительность разговора")
    recording_url = models.CharField(max_length=500, blank=True, default="", verbose_name="URL записи")
    transcription_status = models.CharField(
        max_length=32,
        choices=PhoneCallTranscriptionStatus.choices,
        default=PhoneCallTranscriptionStatus.NOT_REQUESTED,
        verbose_name="Статус транскрибации",
    )
    transcription_external_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Внешний ID транскрибации")
    transcription_recording_url = models.CharField(max_length=500, blank=True, default="", verbose_name="URL записи для транскрибации")
    transcription_text = models.TextField(blank=True, default="", verbose_name="Текст транскрибации")
    transcription_error = models.TextField(blank=True, default="", verbose_name="Ошибка транскрибации")
    transcription_requested_at = models.DateTimeField(blank=True, null=True, verbose_name="Транскрибация запрошена")
    transcription_completed_at = models.DateTimeField(blank=True, null=True, verbose_name="Транскрибация завершена")
    raw_payload_last = models.JSONField(default=dict, blank=True, verbose_name="Последний payload")

    class Meta:
        verbose_name = "Телефонный звонок"
        verbose_name_plural = "Телефонные звонки"
        ordering = ("-started_at", "-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_call_id"],
                condition=~models.Q(external_call_id=""),
                name="integrations_unique_provider_external_call_id",
            ),
        ]
        indexes = [
            models.Index(fields=["external_call_id"]),
            models.Index(fields=["client_phone_normalized"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["crm_user"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["transcription_external_id"]),
            models.Index(fields=["transcription_status"]),
        ]

    def __str__(self):
        return self.external_call_id or f"call-{self.pk}"


class TelephonyEventLog(models.Model):
    provider = models.CharField(max_length=32, choices=TelephonyProvider.choices, verbose_name="Провайдер")
    event_type = models.CharField(max_length=128, blank=True, default="", verbose_name="Тип события")
    external_event_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Внешний ID события")
    external_call_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Внешний ID звонка")
    deduplication_key = models.CharField(max_length=255, blank=True, default="", verbose_name="Ключ дедупликации")
    payload_json = models.JSONField(default=dict, blank=True, verbose_name="Payload")
    headers_json = models.JSONField(default=dict, blank=True, verbose_name="Headers")
    status = models.CharField(max_length=32, choices=TelephonyEventStatus.choices, default=TelephonyEventStatus.RECEIVED, verbose_name="Статус")
    error_text = models.TextField(blank=True, default="", verbose_name="Ошибка")
    received_at = models.DateTimeField(auto_now_add=True, verbose_name="Получено")
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="Обработано")
    retry_count = models.PositiveIntegerField(default=0, verbose_name="Количество попыток")

    class Meta:
        verbose_name = "Событие телефонии"
        verbose_name_plural = "События телефонии"
        ordering = ("-received_at", "-id")
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["provider", "external_call_id"]),
            models.Index(fields=["deduplication_key"]),
            models.Index(fields=["external_event_id"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.event_type}:{self.external_call_id or self.external_event_id or self.pk}"
