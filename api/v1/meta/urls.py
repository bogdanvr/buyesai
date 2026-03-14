from django.urls import path

from api.v1.meta.views import (
    DealStageListAPIView,
    LeadSourceListAPIView,
    LeadStatusListAPIView,
)

urlpatterns = [
    path("lead-statuses/", LeadStatusListAPIView.as_view(), name="meta-lead-statuses"),
    path("deal-stages/", DealStageListAPIView.as_view(), name="meta-deal-stages"),
    path("lead-sources/", LeadSourceListAPIView.as_view(), name="meta-lead-sources"),
]
