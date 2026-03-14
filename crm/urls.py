from django.urls import path

from crm.views import crm_dashboard

urlpatterns = [
    path("", crm_dashboard, name="crm-dashboard"),
]
