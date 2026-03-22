from rest_framework.routers import DefaultRouter

from api.v1.lead_documents.views import LeadDocumentViewSet

router = DefaultRouter()
router.register("", LeadDocumentViewSet, basename="lead-documents")

urlpatterns = router.urls
