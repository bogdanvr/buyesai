from django.db import models

from crm.models.common import TimestampedModel


class AutomationTouchpointMode(models.TextChoices):
    NONE = "none", "Не создавать"
    DRAFT = "draft", "Черновик"
    CREATE = "create", "Создать"


class AutomationRule(TimestampedModel):
    event_type = models.CharField(max_length=64, unique=True, verbose_name="Тип события")
    write_timeline = models.BooleanField(default=True, verbose_name="Писать в ленту")
    create_message = models.BooleanField(default=False, verbose_name="Создавать сообщение")
    create_touchpoint_mode = models.CharField(
        max_length=16,
        choices=AutomationTouchpointMode.choices,
        default=AutomationTouchpointMode.NONE,
        verbose_name="Режим создания касания",
    )
    default_outcome_code = models.CharField(max_length=64, blank=True, default="", verbose_name="Код результата по умолчанию")
    require_manager_confirmation = models.BooleanField(default=False, verbose_name="Требовать подтверждение менеджера")
    suggest_next_step_template = models.CharField(max_length=128, blank=True, default="", verbose_name="Шаблон следующего шага")
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Правило автоматизации"
        verbose_name_plural = "Правила автоматизации"
        ordering = ("event_type",)

    def __str__(self):
        return self.event_type
