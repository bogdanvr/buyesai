from rest_framework.generics import ListAPIView

from api.v1.meta.serializers import (
    DealStageSerializer,
    LeadSourceSerializer,
    LeadStatusSerializer,
)
from crm.models import DealStage, LeadSource, LeadStatus


class LeadStatusListAPIView(ListAPIView):
    serializer_class = LeadStatusSerializer
    pagination_class = None

    def get_queryset(self):
        return LeadStatus.objects.filter(is_active=True).order_by("order", "name")


class DealStageListAPIView(ListAPIView):
    serializer_class = DealStageSerializer
    pagination_class = None

    def get_queryset(self):
        return DealStage.objects.filter(is_active=True).order_by("order", "name")


class LeadSourceListAPIView(ListAPIView):
    serializer_class = LeadSourceSerializer
    pagination_class = None

    def get_queryset(self):
        return LeadSource.objects.filter(is_active=True).order_by("name")
