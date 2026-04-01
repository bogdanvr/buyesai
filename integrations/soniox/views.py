from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.soniox.services import process_soniox_transcription_webhook


class SonioxWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        try:
            result = process_soniox_transcription_webhook(payload=payload, headers=dict(request.headers.items()))
        except ValueError as error:
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"ok": True, "result": result}, status=status.HTTP_202_ACCEPTED)
