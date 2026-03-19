from django.db import models

from crm.models.common import TimestampedModel


class Client(TimestampedModel):
    CURRENCY_CHOICES = (
        ("RUB", "RUB"),
        ("KZT", "KZT"),
        ("USD", "USD"),
        ("EUR", "EUR"),
    )

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
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="RUB",
        verbose_name="Валюта компании",
    )
    website = models.URLField(blank=True, default="", verbose_name="Сайт")
    address = models.CharField(max_length=512, blank=True, default="", verbose_name="Адрес")
    actual_address = models.CharField(max_length=512, blank=True, default="", verbose_name="Фактический адрес")
    bank_details = models.TextField(blank=True, default="", verbose_name="Банковские реквизиты")
    iban = models.CharField(max_length=128, blank=True, default="", verbose_name="ИИК / IBAN")
    bik = models.CharField(max_length=64, blank=True, default="", verbose_name="БИК")
    bank_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Банк")
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
    work_rules = models.JSONField(default=dict, blank=True, verbose_name="Правила работы")
    notes = models.TextField(blank=True, default="", verbose_name="Заметки")
    events = models.TextField(blank=True, default="", verbose_name="События")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"
        ordering = ("name",)

    def __str__(self):
        return self.name


class CommunicationChannel(TimestampedModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="Канал связи")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Канал связи"
        verbose_name_plural = "Каналы связи"
        ordering = ("name",)

    def __str__(self):
        return self.name
