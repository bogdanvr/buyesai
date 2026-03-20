from django.urls import path

from crm.views import crm_asset_fallback, crm_dashboard

urlpatterns = [
    path("", crm_dashboard, name="crm-dashboard"),
    path("_asset/<str:asset_type>/<path:filename>", crm_asset_fallback, name="crm-asset-fallback"),
]
