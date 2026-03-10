from django.contrib import admin

from main.models import Implementation, Case, Department, FormSubmission

@admin.register(Implementation)
class ImplementationAdmin(admin.ModelAdmin):
    list_display = ('step', 'title', 'period')


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'solution')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('title',)


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "form_type",
        "name",
        "phone",
        "company",
        "telegram_sent",
        "telegram_sent_count",
        "telegram_total_targets",
    )
    list_filter = ("form_type", "created_at", "telegram_sent")
    search_fields = ("name", "phone", "company", "message")
    readonly_fields = (
        "created_at",
        "telegram_sent",
        "telegram_sent_count",
        "telegram_total_targets",
        "telegram_errors",
    )
