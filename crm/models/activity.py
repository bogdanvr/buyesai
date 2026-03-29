from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import uuid

from crm.models.common import TimestampedModel


class ActivityType(models.TextChoices):
    CALL = "call", "Звонок"
    EMAIL = "email", "Email"
    MEETING = "meeting", "Встреча"
    NOTE = "note", "Заметка"
    TASK = "task", "Задача"


class TaskStatus(models.TextChoices):
    TODO = "todo", "Новая"
    IN_PROGRESS = "in_progress", "В работе"
    DONE = "done", "Выполнено"
    CANCELED = "canceled", "Отменено"


class TaskPriority(models.TextChoices):
    LOW = "low", "Низкий"
    MEDIUM = "medium", "Средний"
    HIGH = "high", "Высокий"


class TaskReminderOffset(models.IntegerChoices):
    MINUTES_5 = 5, "5 минут"
    MINUTES_10 = 10, "10 минут"
    MINUTES_15 = 15, "15 минут"
    MINUTES_30 = 30, "30 минут"
    HOURS_1 = 60, "1 час"
    HOURS_2 = 120, "2 часа"
    HOURS_3 = 180, "3 часа"


class TaskTypeGroup(models.TextChoices):
    INTERNAL_TASK = "internal_task", "Внутренняя задача"
    CLIENT_TASK = "client_task", "Клиентская задача"


class UserRole(TimestampedModel):
    code = models.CharField(max_length=64, unique=True, verbose_name="Код")
    name = models.CharField(max_length=128, unique=True, verbose_name="Название роли")
    sort_order = models.PositiveIntegerField(default=100, verbose_name="Порядок сортировки")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Роль пользователя"
        verbose_name_plural = "Роли пользователей"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not str(self.code or "").strip():
            self.code = slugify(self.name or "", allow_unicode=False).replace("-", "_") or f"role_{self.pk or 'new'}"
        super().save(*args, **kwargs)


class UserRoleAssignment(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_user_role_assignments",
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )
    role = models.ForeignKey(
        "crm.UserRole",
        related_name="assignments",
        on_delete=models.CASCADE,
        verbose_name="Роль",
    )

    class Meta:
        verbose_name = "Назначение роли пользователю"
        verbose_name_plural = "Назначения ролей пользователям"
        ordering = ("user__username", "role__sort_order", "role__name")
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="unique_crm_user_role_assignment"),
        ]

    def __str__(self):
        return f"{self.user} → {self.role}"


class TaskCategory(TimestampedModel):
    code = models.CharField(max_length=64, unique=True, verbose_name="Код")
    name = models.CharField(max_length=128, unique=True, verbose_name="Название категории")
    sort_order = models.PositiveIntegerField(default=100, verbose_name="Порядок сортировки")
    group = models.CharField(
        max_length=32,
        choices=TaskTypeGroup.choices,
        blank=True,
        default="",
        verbose_name="Группа задач",
    )
    uses_communication_channel = models.BooleanField(
        default=False,
        verbose_name="Использует канал связи",
    )
    requires_follow_up_task_on_done = models.BooleanField(
        default=False,
        verbose_name="Требует следующую задачу при завершении",
    )
    satisfies_deal_next_step_requirement = models.BooleanField(
        default=False,
        verbose_name="Закрывает требование следующего шага по сделке",
    )
    allowed_roles = models.ManyToManyField(
        "crm.UserRole",
        related_name="task_categories",
        blank=True,
        verbose_name="Доступные роли",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Категория задачи"
        verbose_name_plural = "Категории задач"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not str(self.code or "").strip():
            self.code = slugify(self.name or "", allow_unicode=False).replace("-", "_") or f"task_category_{self.pk or 'new'}"
        self.group = TaskTypeGroup.CLIENT_TASK if self.uses_communication_channel else TaskTypeGroup.INTERNAL_TASK
        super().save(*args, **kwargs)


class TaskType(TimestampedModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="Тип задачи")
    sort_order = models.PositiveIntegerField(default=100, verbose_name="Порядок сортировки")
    group = models.CharField(
        max_length=32,
        choices=TaskTypeGroup.choices,
        default=TaskTypeGroup.INTERNAL_TASK,
        verbose_name="Группа задач",
    )
    category = models.ForeignKey(
        "crm.TaskCategory",
        related_name="task_types",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Категория задачи",
    )
    auto_touch_on_done = models.BooleanField(default=False, verbose_name="Автокасание")
    touch_result = models.CharField(max_length=128, blank=True, default="", verbose_name="Результат")
    auto_task_on_done = models.BooleanField(default=False, verbose_name="Автозадача")
    auto_task_type = models.ForeignKey(
        "self",
        related_name="auto_created_from_types",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Тип автозадачи",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Тип задачи"
        verbose_name_plural = "Типы задач"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        category = getattr(self, "category", None)
        if category is not None:
            self.group = TaskTypeGroup.CLIENT_TASK if getattr(category, "uses_communication_channel", False) else TaskTypeGroup.INTERNAL_TASK
        super().save(*args, **kwargs)


def get_available_task_categories_for_user(user):
    queryset = TaskCategory.objects.filter(is_active=True)
    if getattr(user, "is_superuser", False):
        return queryset
    if user is None or not getattr(user, "is_authenticated", False):
        return queryset.filter(allowed_roles__isnull=True).distinct()
    return queryset.filter(
        models.Q(allowed_roles__isnull=True)
        | models.Q(allowed_roles__is_active=True, allowed_roles__assignments__user=user)
    ).distinct()


def get_available_task_types_for_user(user):
    queryset = TaskType.objects.filter(is_active=True).select_related("category")
    if getattr(user, "is_superuser", False):
        return queryset
    if user is None or not getattr(user, "is_authenticated", False):
        return queryset.filter(models.Q(category__isnull=True) | models.Q(category__allowed_roles__isnull=True)).distinct()
    return queryset.filter(
        models.Q(category__isnull=True)
        | models.Q(category__allowed_roles__isnull=True)
        | models.Q(category__allowed_roles__is_active=True, category__allowed_roles__assignments__user=user)
    ).distinct()


def get_task_type_category(task_type):
    return getattr(task_type, "category", None) if task_type is not None else None


def task_type_uses_communication_channel(task_type) -> bool:
    category = get_task_type_category(task_type)
    if category is not None:
        return bool(getattr(category, "uses_communication_channel", False))
    return str(getattr(task_type, "group", "") or "").strip() == TaskTypeGroup.CLIENT_TASK


def task_type_requires_follow_up_task(task_type) -> bool:
    category = get_task_type_category(task_type)
    if category is not None:
        return bool(getattr(category, "requires_follow_up_task_on_done", False))
    return str(getattr(task_type, "group", "") or "").strip() == TaskTypeGroup.INTERNAL_TASK


def task_type_satisfies_deal_next_step_requirement(task_type) -> bool:
    category = get_task_type_category(task_type)
    if category is not None:
        return bool(getattr(category, "satisfies_deal_next_step_requirement", False))
    return str(getattr(task_type, "group", "") or "").strip() == TaskTypeGroup.CLIENT_TASK


class Activity(TimestampedModel):
    type = models.CharField(
        max_length=16,
        choices=ActivityType.choices,
        default=ActivityType.NOTE,
        verbose_name="Тип",
    )
    subject = models.CharField(max_length=255, verbose_name="Тема")
    description = models.TextField(blank=True, default="", verbose_name="Описание")
    result = models.TextField(blank=True, default="", verbose_name="Результат")
    due_at = models.DateTimeField(blank=True, null=True, verbose_name="Срок")
    status = models.CharField(
        max_length=16,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
        verbose_name="Статус задачи",
    )
    priority = models.CharField(
        max_length=16,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
        verbose_name="Приоритет",
    )
    task_type = models.ForeignKey(
        "crm.TaskType",
        related_name="activities",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Тип задачи",
    )
    communication_channel = models.ForeignKey(
        "crm.CommunicationChannel",
        related_name="activities",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Канал связи",
    )
    related_touch = models.ForeignKey(
        "self",
        related_name="related_tasks",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Связанное касание",
    )
    deadline_reminder_offset_minutes = models.PositiveSmallIntegerField(
        choices=TaskReminderOffset.choices,
        default=TaskReminderOffset.MINUTES_30,
        verbose_name="Напомнить за",
    )
    checklist = models.JSONField(default=list, blank=True, verbose_name="Чек-лист")
    deadline_reminder_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Напоминание о дедлайне отправлено",
    )
    deadline_reminder_ack_token = models.CharField(
        max_length=32,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Токен подтверждения напоминания",
    )
    deadline_reminder_acknowledged_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Напоминание подтверждено",
    )
    deadline_reminder_email_escalated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Эскалация на email отправлена",
    )
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="Выполнено")
    is_done = models.BooleanField(default=False, verbose_name="Завершено")
    save_company_note = models.BooleanField(
        default=False,
        verbose_name="Сохранить значимую информацию в компании",
    )
    company_note = models.TextField(blank=True, default="", verbose_name="Факты о компании")
    lead = models.ForeignKey(
        "crm.Lead",
        related_name="activities",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Лид",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        related_name="activities",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Сделка",
    )
    client = models.ForeignKey(
        "crm.Client",
        related_name="activities",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Клиент",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        related_name="activities",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Контакт",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_activities",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Автор",
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["is_done"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_at"]),
        ]

    def __str__(self):
        return self.subject

    def mark_done(self):
        self.status = TaskStatus.DONE
        self.is_done = True
        if self.completed_at is None:
            self.completed_at = timezone.now()

    @property
    def is_task_active(self) -> bool:
        return self.type == ActivityType.TASK and self.status in {
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
        }

    def ensure_deadline_ack_token(self) -> str:
        if not self.deadline_reminder_ack_token:
            self.deadline_reminder_ack_token = uuid.uuid4().hex
        return self.deadline_reminder_ack_token

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if self.type == ActivityType.TASK:
            if self.status != TaskStatus.DONE and self.is_done:
                self.status = TaskStatus.DONE
            elif self.status == TaskStatus.DONE and not self.is_done:
                self.status = TaskStatus.TODO
            if self.status == TaskStatus.DONE:
                self.is_done = True
                if self.completed_at is None:
                    self.completed_at = timezone.now()
            else:
                self.is_done = False
                self.completed_at = None
            if update_fields is not None:
                normalized_fields = set(update_fields)
                normalized_fields.update({"status", "is_done", "completed_at"})
                kwargs["update_fields"] = list(normalized_fields)
        super().save(*args, **kwargs)
