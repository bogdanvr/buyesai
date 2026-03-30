from django.urls import path
from rest_framework.routers import DefaultRouter

from api.v1.settlements.views import (
    SettlementAllocationViewSet,
    SettlementContractViewSet,
    SettlementDocumentViewSet,
    SettlementSummaryAPIView,
)

router = DefaultRouter()
router.register("contracts", SettlementContractViewSet, basename="settlement-contracts")
router.register("documents", SettlementDocumentViewSet, basename="settlement-documents")
router.register("allocations", SettlementAllocationViewSet, basename="settlement-allocations")

urlpatterns = [
    path("summary/", SettlementSummaryAPIView.as_view(), name="settlement-summary"),
    *router.urls,
]
