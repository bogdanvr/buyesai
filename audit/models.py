from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    action = models.CharField(max_length=128, verbose_name="Действие")
    app_label = models.CharField(max_length=64, verbose_name="Приложение")
    model = models.CharField(max_length=64, verbose_name="Модель")
    object_id = models.CharField(max_length=64, verbose_name="ID объекта")
    payload = models.JSONField(default=dict, blank=True, verbose_name="Payload")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audit_logs",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Пользователь",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Записи аудита"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["app_label", "model"]),
            models.Index(fields=["object_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} {self.app_label}.{self.model}#{self.object_id}"
