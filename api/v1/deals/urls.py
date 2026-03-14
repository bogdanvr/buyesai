from rest_framework.routers import DefaultRouter

from api.v1.deals.views import DealViewSet

router = DefaultRouter()
router.register("", DealViewSet, basename="deals")

urlpatterns = router.urls
