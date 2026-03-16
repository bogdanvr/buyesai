from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.webhooks.serializers import WebhookCreateSerializer, WebhookEventSerializer
from integrations.services.webhooks import process_webhook_event, store_webhook_event


class WebhookReceiveAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = WebhookCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = store_webhook_event(**serializer.validated_data)
        result = process_webhook_event(event)
        response_data = {
            "event": WebhookEventSerializer(event).data,
            "result": result,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class TelegramWebhookReceiveAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        event = store_webhook_event(
            source="telegram",
            event_type="telegram_update",
            external_id=str(payload.get("update_id") or ""),
            payload=payload,
        )
        result = process_webhook_event(event)
        return Response({"ok": True, "result": result}, status=status.HTTP_200_OK)
