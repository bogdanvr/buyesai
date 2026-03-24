from django.db import models

from crm.models.common import TimestampedModel


class LeadStatus(TimestampedModel):
    name = models.CharField(max_length=128, verbose_name="Статус")
    code = models.SlugField(max_length=64, unique=True, verbose_name="Код")
    order = models.PositiveSmallIntegerField(default=100, verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_final = models.BooleanField(default=False, verbose_name="Финальный")
    touch_results = models.ManyToManyField(
        "crm.TouchResult",
        related_name="lead_statuses",
        blank=True,
        verbose_name="Результаты касаний",
    )

    class Meta:
        verbose_name = "Статус лида"
        verbose_name_plural = "Статусы лидов"
        ordering = ("order", "name")

    def __str__(self):
        return self.name


class DealStage(TimestampedModel):
    name = models.CharField(max_length=128, verbose_name="Этап")
    code = models.SlugField(max_length=64, unique=True, verbose_name="Код")
    order = models.PositiveSmallIntegerField(default=100, verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_final = models.BooleanField(default=False, verbose_name="Финальный")
    touch_results = models.ManyToManyField(
        "crm.TouchResult",
        related_name="deal_stages",
        blank=True,
        verbose_name="Результаты касаний",
    )

    class Meta:
        verbose_name = "Этап сделки"
        verbose_name_plural = "Этапы сделок"
        ordering = ("order", "name")

    def __str__(self):
        return self.name
