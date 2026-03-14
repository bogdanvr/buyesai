from django.conf import settings
from django.db import models
from django.utils import timezone

from crm.models.common import TimestampedModel


class ActivityType(models.TextChoices):
    CALL = "call", "Звонок"
    EMAIL = "email", "Email"
    MEETING = "meeting", "Встреча"
    NOTE = "note", "Заметка"
    TASK = "task", "Задача"


class Activity(TimestampedModel):
    type = models.CharField(
        max_length=16,
        choices=ActivityType.choices,
        default=ActivityType.NOTE,
        verbose_name="Тип",
    )
    subject = models.CharField(max_length=255, verbose_name="Тема")
    description = models.TextField(blank=True, default="", verbose_name="Описание")
    due_at = models.DateTimeField(blank=True, null=True, verbose_name="Срок")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="Выполнено")
    is_done = models.BooleanField(default=False, verbose_name="Завершено")
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
