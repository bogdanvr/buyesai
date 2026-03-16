from django.urls import path

from api.v1.webhooks.views import TelegramWebhookReceiveAPIView, WebhookReceiveAPIView

urlpatterns = [
    path("", WebhookReceiveAPIView.as_view(), name="webhooks-receive"),
    path("telegram/", TelegramWebhookReceiveAPIView.as_view(), name="webhooks-telegram"),
]
