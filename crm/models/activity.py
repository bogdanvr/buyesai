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


class TaskReminderOffset(models.IntegerChoices):
    MINUTES_5 = 5, "5 минут"
    MINUTES_10 = 10, "10 минут"
    MINUTES_15 = 15, "15 минут"
    MINUTES_30 = 30, "30 минут"
    HOURS_1 = 60, "1 час"
    HOURS_2 = 120, "2 часа"
    HOURS_3 = 180, "3 часа"


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
            models.Index(fields=["due_at"]),
        ]

    def __str__(self):
        return self.subject

    def mark_done(self):
        self.is_done = True
        if self.completed_at is None:
            self.completed_at = timezone.now()

    def ensure_deadline_ack_token(self) -> str:
        if not self.deadline_reminder_ack_token:
            self.deadline_reminder_ack_token = uuid.uuid4().hex
        return self.deadline_reminder_ack_token
