from django.db import models

from crm.models.common import TimestampedModel


class LeadSource(TimestampedModel):
    name = models.CharField(max_length=128, verbose_name="Действие")
    code = models.SlugField(max_length=64, unique=True, verbose_name="Код")
    description = models.TextField(blank=True, default="", verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Действие на сайте"
        verbose_name_plural = "Действия на сайте"
        ordering = ("name",)

    def __str__(self):
        return self.name


class TrafficSource(TimestampedModel):
    name = models.CharField(max_length=128, verbose_name="Источник")
    code = models.SlugField(max_length=64, unique=True, verbose_name="Код")
    description = models.TextField(blank=True, default="", verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Источник трафика"
        verbose_name_plural = "Источники трафика"
        ordering = ("name",)

    def __str__(self):
        return self.name
