from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid

from crm.models.common import TimestampedModel


class ActivityType(models.TextChoices):
    CALL = "call", "Звонок"
    EMAIL = "email", "Email"
    MEETING = "meeting", "Встреча"
    NOTE = "note", "Заметка"
    TASK = "task", "Задача"


class TaskStatus(models.TextChoices):
    TODO = "todo", "К выполнению"
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


class TaskType(TimestampedModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="Тип задачи")
    group = models.CharField(
        max_length=32,
        choices=TaskTypeGroup.choices,
        default=TaskTypeGroup.INTERNAL_TASK,
        verbose_name="Группа типа задачи",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Тип задачи"
        verbose_name_plural = "Типы задач"
        ordering = ("name",)

    def __str__(self):
        return self.name


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
        verbose_name = "Активность"
        verbose_name_plural = "Активности"
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
