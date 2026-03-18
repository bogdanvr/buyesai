from rest_framework.routers import DefaultRouter

from api.v1.touches.views import TouchViewSet

router = DefaultRouter()
router.register("", TouchViewSet, basename="touches")

urlpatterns = router.urls
