from rest_framework.routers import DefaultRouter

from api.v1.deal_documents.views import DealDocumentViewSet

router = DefaultRouter()
router.register("", DealDocumentViewSet, basename="deal-documents")

urlpatterns = router.urls
