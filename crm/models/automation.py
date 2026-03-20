from django.db import models


class AutomationTouchpointMode(models.TextChoices):
    NONE = "none", "Не создавать"
    DRAFT = "draft", "Черновик"
    CREATE = "create", "Создать"


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
    write_timeline = models.BooleanField(default=True, verbose_name="Писать в ленту")
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
