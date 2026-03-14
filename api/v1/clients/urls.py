from rest_framework.routers import DefaultRouter

from api.v1.clients.views import ClientViewSet

router = DefaultRouter()
router.register("", ClientViewSet, basename="clients")

urlpatterns = router.urls
