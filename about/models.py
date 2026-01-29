from tabnanny import verbose
from django.db import models


class Contact(models.Model):
    phone = models.CharField(max_length=12, verbose_name='Телефон')
    address = models.CharField(max_length=256, verbose_name='Адрес')


class Merit(models.Model):
    title = models.CharField(max_length=250, verbose_name='Наименование')

    class Meta:
        verbose_name = 'Заслугу'
        verbose_name_plural = 'Заслуги'
    
    def __str__(self):
        return self.title


class Staff(models.Model):
    title = models.CharField(max_length=250, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')

    class Meta:
        verbose_name = 'Персонал'
        verbose_name_plural = 'Персонал'
    
    def __str__(self):
        return self.title


class Team(models.Model):
    title = models.CharField(max_length=125, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    common_merits = models.ManyToManyField(Merit, verbose_name='Заслуги компании')
    second_description = models.TextField(verbose_name='Второе описание')
    staff = models.ManyToManyField(Staff, verbose_name='Сотрудники')

    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команда'
    
    def __str__(self):
        return self.title
    
