from django.db import models

from crm.models.common import TimestampedModel


class Client(TimestampedModel):
    name = models.CharField(max_length=255, verbose_name="Клиент")
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Юридическое название",
    )
    inn = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        unique=True,
        verbose_name="ИНН",
    )
    phone = models.CharField(max_length=64, blank=True, default="", verbose_name="Телефон")
    email = models.EmailField(blank=True, default="", verbose_name="Email")
    website = models.URLField(blank=True, default="", verbose_name="Сайт")
    address = models.CharField(max_length=512, blank=True, default="", verbose_name="Адрес")
    industry = models.CharField(max_length=255, blank=True, default="", verbose_name="Сфера деятельности")
    okved = models.CharField(max_length=64, blank=True, default="", verbose_name="ОКВЭД")
    okveds = models.JSONField(default=list, blank=True, verbose_name="ОКВЭД (все виды)")
    source = models.ForeignKey(
        "crm.LeadSource",
        related_name="clients",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Источник",
    )
    notes = models.TextField(blank=True, default="", verbose_name="Заметки")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"
        ordering = ("name",)

    def __str__(self):
        return self.name
