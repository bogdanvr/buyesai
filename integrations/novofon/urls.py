from django.urls import path

from integrations.novofon.views import (
    NovofonCallAPIView,
    NovofonCheckConnectionAPIView,
    NovofonSettingsAPIView,
    NovofonSyncEmployeesAPIView,
    NovofonWebhookAPIView,
    PhoneCallDetailAPIView,
    PhoneCallListAPIView,
    TelephonyEventReprocessAPIView,
)


urlpatterns = [
    path("settings/", NovofonSettingsAPIView.as_view(), name="telephony-novofon-settings"),
    path("check-connection/", NovofonCheckConnectionAPIView.as_view(), name="telephony-novofon-check-connection"),
    path("sync-employees/", NovofonSyncEmployeesAPIView.as_view(), name="telephony-novofon-sync-employees"),
    path("call/", NovofonCallAPIView.as_view(), name="telephony-novofon-call"),
    path("calls/", PhoneCallListAPIView.as_view(), name="telephony-calls"),
    path("calls/<int:pk>/", PhoneCallDetailAPIView.as_view(), name="telephony-call-detail"),
    path("events/<int:pk>/reprocess/", TelephonyEventReprocessAPIView.as_view(), name="telephony-event-reprocess"),
    path("webhook/", NovofonWebhookAPIView.as_view(), name="integrations-novofon-webhook"),
]
