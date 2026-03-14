from rest_framework.routers import DefaultRouter

from api.v1.activities.views import ActivityViewSet

router = DefaultRouter()
router.register("", ActivityViewSet, basename="activities")

urlpatterns = router.urls
