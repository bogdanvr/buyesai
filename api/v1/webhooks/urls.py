from django.urls import path

from api.v1.webhooks.views import WebhookReceiveAPIView

urlpatterns = [
    path("", WebhookReceiveAPIView.as_view(), name="webhooks-receive"),
]
