from django.db import models


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
