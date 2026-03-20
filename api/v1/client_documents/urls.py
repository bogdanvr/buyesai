from rest_framework.routers import DefaultRouter

from api.v1.client_documents.views import ClientDocumentViewSet

router = DefaultRouter()
router.register("", ClientDocumentViewSet, basename="client-documents")

urlpatterns = router.urls
