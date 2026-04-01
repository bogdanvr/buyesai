from django.conf import settings
from django.db import models
from pathlib import Path

from crm.models.common import TimestampedModel


def truncate_upload_filename(filename: str, max_stem_length: int = 120) -> str:
    safe_name = Path(str(filename or "document")).name or "document"
    path = Path(safe_name)
    suffix = path.suffix or ""
    stem = path.stem or "document"
    if len(stem) <= max_stem_length:
        return f"{stem}{suffix}"
    return f"{stem[:max_stem_length]}{suffix}"


def client_document_upload_to(instance, filename: str) -> str:
    client_id = getattr(instance, "client_id", None) or getattr(getattr(instance, "client", None), "id", None) or "new"
    safe_name = truncate_upload_filename(filename)
    return f"company_{client_id}/company/{safe_name}"


class Client(TimestampedModel):
    class CompanyType(models.TextChoices):
        OWN = "own", "Собственные организации"
        CLIENT = "client", "Клиент"
        SUPPLIER = "supplier", "Поставщик"

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
    company_type = models.CharField(
        max_length=16,
        choices=CompanyType.choices,
        default=CompanyType.CLIENT,
        verbose_name="Тип компании",
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="RUB",
        verbose_name="Валюта компании",
    )
    website = models.URLField(blank=True, default="", verbose_name="Сайт")
    address = models.CharField(max_length=512, blank=True, default="", verbose_name="Адрес")
    actual_address = models.CharField(max_length=512, blank=True, default="", verbose_name="Фактический адрес")
    ogrn = models.CharField(max_length=15, blank=True, default="", verbose_name="ОГРН")
    kpp = models.CharField(max_length=9, blank=True, default="", verbose_name="КПП")
    bank_details = models.TextField(blank=True, default="", verbose_name="Банковские реквизиты")
    settlement_account = models.CharField(max_length=64, blank=True, default="", verbose_name="Расчетный счет")
    correspondent_account = models.CharField(max_length=64, blank=True, default="", verbose_name="Корреспондентский счет")
    iban = models.CharField(max_length=128, blank=True, default="", verbose_name="ИИК / IBAN")
    bik = models.CharField(max_length=64, blank=True, default="", verbose_name="БИК")
    bank_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Банк")
    industry = models.CharField(max_length=255, blank=True, default="", verbose_name="Сфера деятельности")
    okved = models.CharField(max_length=64, blank=True, default="", verbose_name="ОКВЭД")
    okveds = models.JSONField(default=list, blank=True, verbose_name="ОКВЭД (все виды)")
    source = models.ForeignKey(
        "crm.TrafficSource",
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
    touch_results = models.ManyToManyField(
        "crm.TouchResult",
        related_name="communication_channels",
        blank=True,
        verbose_name="Допустимые результаты касаний",
    )

    class Meta:
        verbose_name = "Канал связи"
        verbose_name_plural = "Каналы связи"
        ordering = ("name",)

    def __str__(self):
        return self.name


class ClientDocument(TimestampedModel):
    client = models.ForeignKey(
        "crm.Client",
        related_name="documents",
        on_delete=models.CASCADE,
        verbose_name="Компания",
    )
    file = models.FileField(upload_to=client_document_upload_to, max_length=500, verbose_name="Файл")
    original_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Название файла")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="crm_client_documents",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Загрузил",
    )

    class Meta:
        verbose_name = "Документ компании"
        verbose_name_plural = "Документы компаний"
        ordering = ("-created_at", "-id")

    def __str__(self):
        return self.original_name or self.file.name.rsplit("/", 1)[-1] or f"Документ #{self.pk}"
