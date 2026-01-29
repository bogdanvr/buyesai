from django.contrib import admin
from about.models import Team, Staff


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('title', 'description')


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('title', 'description')