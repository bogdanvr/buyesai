from django.db import models


class Actions(models.Model):
    title = models.CharField(max_length=2503, verbose_name='Действие')

    class Meta:
        verbose_name = 'Действие'
        verbose_name_plural = 'Действия'
    
    def __str__(self):
        return self.title


class Implementation(models.Model):
    step = models.IntegerField(verbose_name="Номера шага")
    title = models.CharField(max_length=125, verbose_name='Название')
    period = models.CharField(max_length=125, verbose_name='Срок реализации')
    list_actions = models.ForeignKey(Actions, related_name='actionsimplementations',
                                      on_delete=models.CASCADE,
                                      verbose_name='Список действий')
    
    class Meta:
        verbose_name = 'Внедрение'
        verbose_name_plural = 'Внедрения'
    
    def __str__(self):
        return self.title


class Department(models.Model):
    title = models.CharField(max_length=125, verbose_name = 'Название')

    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'
    
    def __str__(self):
        return self.title


class Improvements(models.Model):
    title = models.CharField(max_length=250, verbose_name='Наименование')
    result = models.CharField(max_length=250, verbose_name='Результат')

    class Meta:
        verbose_name = 'Улучшение'
        verbose_name_plural = 'Улучшения'
    
    def __str__(self):
        return self.title


class Case(models.Model):
    department = models.ForeignKey(Department, related_name='departmentcase',
                                   on_delete=models.CASCADE, verbose_name='Подразделение')
    title = models.CharField(max_length=250, verbose_name='Название')
    improvements = models.ForeignKey(Improvements, related_name='improvementscase',
                                     on_delete=models.CASCADE, verbose_name='Улучшение')
    solution = models.CharField(max_length=250, verbose_name='Решение')

    class Meta:
        verbose_name = 'Кейс'
        verbose_name_plural = 'Кейсы'
    
    def __str__(self):
        return self.title


class FormSubmission(models.Model):
    form_type = models.CharField(max_length=64, verbose_name="Тип формы", db_index=True)
    name = models.CharField(max_length=255, blank=True, default="", verbose_name="Имя")
    phone = models.CharField(max_length=64, blank=True, default="", verbose_name="Телефон")
    company = models.CharField(max_length=255, blank=True, default="", verbose_name="Компания")
    message = models.TextField(blank=True, default="", verbose_name="Сообщение")
    payload = models.JSONField(default=dict, blank=True, verbose_name="Полезная нагрузка")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Отправка формы"
        verbose_name_plural = "Отправки форм"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.form_type} #{self.pk}"



