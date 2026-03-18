from django.contrib.auth import get_user_model
from django.core import signing
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from api.v1.filters import apply_text_search
from api.v1.leads.serializers import LeadSerializer
from crm.selectors.lead_selectors import list_leads


User = get_user_model()


class LeadViewSet(ModelViewSet):
    serializer_class = LeadSerializer

    def get_queryset(self):
        queryset = list_leads()
        status_code = self.request.query_params.get("status")
        source_code = self.request.query_params.get("source")
        search_query = self.request.query_params.get("q")

        if status_code:
            queryset = queryset.filter(status__code=status_code)
        if source_code:
            queryset = queryset.filter(source__code=source_code)
        queryset = apply_text_search(
            queryset,
            search_query,
            ["title", "name", "phone", "email", "company", "external_id"],
        )
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)


class LeadAcceptByEmailAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        signed_token = str(request.query_params.get("token") or "").strip()
        if not signed_token:
            return HttpResponse("Отсутствует токен принятия лида.", status=400)

        try:
            payload = signing.loads(signed_token, salt="lead-accept-email", max_age=60 * 60 * 24 * 7)
        except signing.SignatureExpired:
            return HttpResponse("Срок действия ссылки истёк.", status=400)
        except signing.BadSignature:
            return HttpResponse("Ссылка принятия лида недействительна.", status=400)

        lead_id = payload.get("lead_id")
        user_id = payload.get("user_id")
        token = str(payload.get("token") or "").strip()

        lead = list_leads().filter(pk=lead_id, assignment_notification_token=token).first()
        if lead is None:
            return HttpResponse("Лид не найден.", status=404)

        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return HttpResponse("Пользователь не найден.", status=404)

        if lead.assigned_to_id is None:
            lead.assigned_to = user
            lead.assignment_notification_accepted_at = timezone.now()
            lead.save(update_fields=["assigned_to", "assignment_notification_accepted_at", "updated_at"])
            return HttpResponse("Лид принят. Вы назначены ответственным.", status=200)
        if lead.assigned_to_id == user.pk:
            return HttpResponse("Вы уже назначены ответственным по этому лиду.", status=200)
        return HttpResponse("Лид уже принят другим пользователем.", status=409)
