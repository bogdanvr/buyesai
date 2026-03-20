from django.urls import path

from api.v1.meta.views import (
    AutomationRuleListAPIView,
    CommunicationChannelListAPIView,
    ContactRoleListAPIView,
    ContactStatusListAPIView,
    CurrencyRatesAPIView,
    DealStageListAPIView,
    LeadSourceListAPIView,
    LeadStatusListAPIView,
    NextStepTemplateListAPIView,
    OutcomeCatalogListAPIView,
    TaskTypeListAPIView,
    TouchResultListAPIView,
    UserOptionListAPIView,
)

urlpatterns = [
    path("lead-statuses/", LeadStatusListAPIView.as_view(), name="meta-lead-statuses"),
    path("deal-stages/", DealStageListAPIView.as_view(), name="meta-deal-stages"),
    path("lead-sources/", LeadSourceListAPIView.as_view(), name="meta-lead-sources"),
    path("communication-channels/", CommunicationChannelListAPIView.as_view(), name="meta-communication-channels"),
    path("contact-roles/", ContactRoleListAPIView.as_view(), name="meta-contact-roles"),
    path("contact-statuses/", ContactStatusListAPIView.as_view(), name="meta-contact-statuses"),
    path("users/", UserOptionListAPIView.as_view(), name="meta-users"),
    path("task-types/", TaskTypeListAPIView.as_view(), name="meta-task-types"),
    path("touch-results/", TouchResultListAPIView.as_view(), name="meta-touch-results"),
    path("outcomes/", OutcomeCatalogListAPIView.as_view(), name="meta-outcomes"),
    path("next-step-templates/", NextStepTemplateListAPIView.as_view(), name="meta-next-step-templates"),
    path("automation-rules/", AutomationRuleListAPIView.as_view(), name="meta-automation-rules"),
    path("currency-rates/", CurrencyRatesAPIView.as_view(), name="meta-currency-rates"),
]
