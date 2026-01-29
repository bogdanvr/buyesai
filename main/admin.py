from django.contrib import admin

from main.models import Implementation, Case, Department

@admin.register(Implementation)
class ImplementationAdmin(admin.ModelAdmin):
    list_display = ('step', 'title', 'period')


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'solution')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('title',)
