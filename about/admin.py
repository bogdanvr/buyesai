from django.contrib import admin
from crm.admin.site import crm_admin_site
from about.models import Team, Staff, Contact


@admin.register(Contact)
@admin.register(Contact, site=crm_admin_site)
class TeamAdmin(admin.ModelAdmin):
    admin_group = "Контент"
    list_display = ("phone", "address")


@admin.register(Team)
@admin.register(Team, site=crm_admin_site)
class TeamAdmin(admin.ModelAdmin):
    admin_group = "Контент"
    list_display = ("title", "description")


@admin.register(Staff)
@admin.register(Staff, site=crm_admin_site)
class StaffAdmin(admin.ModelAdmin):
    admin_group = "Контент"
    list_display = ("title", "description")
