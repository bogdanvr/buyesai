from django.urls import path

from api.v1.meta.views import (
    CommunicationChannelListAPIView,
    CurrencyRatesAPIView,
    DealStageListAPIView,
    LeadSourceListAPIView,
    LeadStatusListAPIView,
    TaskTypeListAPIView,
    UserOptionListAPIView,
)

urlpatterns = [
    path("lead-statuses/", LeadStatusListAPIView.as_view(), name="meta-lead-statuses"),
    path("deal-stages/", DealStageListAPIView.as_view(), name="meta-deal-stages"),
    path("lead-sources/", LeadSourceListAPIView.as_view(), name="meta-lead-sources"),
    path("communication-channels/", CommunicationChannelListAPIView.as_view(), name="meta-communication-channels"),
    path("users/", UserOptionListAPIView.as_view(), name="meta-users"),
    path("task-types/", TaskTypeListAPIView.as_view(), name="meta-task-types"),
    path("currency-rates/", CurrencyRatesAPIView.as_view(), name="meta-currency-rates"),
]
