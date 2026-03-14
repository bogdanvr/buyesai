from django.db import models

from crm.models.common import TimestampedModel


class Contact(TimestampedModel):
    client = models.ForeignKey(
        "crm.Client",
        related_name="contacts",
        on_delete=models.CASCADE,
        verbose_name="Клиент",
    )
    first_name = models.CharField(max_length=128, blank=True, default="", verbose_name="Имя")
    last_name = models.CharField(max_length=128, blank=True, default="", verbose_name="Фамилия")
    position = models.CharField(max_length=255, blank=True, default="", verbose_name="Должность")
    phone = models.CharField(max_length=32, blank=True, default="", verbose_name="Телефон")
    email = models.EmailField(blank=True, default="", verbose_name="Email")
    is_primary = models.BooleanField(default=False, verbose_name="Основной контакт")

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ("last_name", "first_name")

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        if full_name:
            return full_name
        if self.phone:
            return self.phone
        return f"Контакт #{self.pk}"
