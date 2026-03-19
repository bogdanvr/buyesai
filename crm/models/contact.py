from django.db import models

from crm.models.common import TimestampedModel


class ContactRole(TimestampedModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="Роль контакта")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Роль контакта"
        verbose_name_plural = "Роли контактов"
        ordering = ("name",)

    def __str__(self):
        return self.name


class ContactStatus(TimestampedModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="Статус контакта")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Статус контакта"
        verbose_name_plural = "Статусы контактов"
        ordering = ("name",)

    def __str__(self):
        return self.name


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
    telegram_whatsapp = models.CharField(max_length=255, blank=True, default="", verbose_name="Telegram / WhatsApp")
    role = models.ForeignKey(
        "crm.ContactRole",
        related_name="contacts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Роль",
    )
    contact_status = models.ForeignKey(
        "crm.ContactStatus",
        related_name="contacts",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Статус контакта",
    )
    person_note = models.TextField(blank=True, default="", verbose_name="Примечание")
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
