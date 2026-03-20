from rest_framework.routers import DefaultRouter

from api.v1.automation_queue.views import AutomationQueueItemViewSet

router = DefaultRouter()
router.register("", AutomationQueueItemViewSet, basename="automation-queue")

urlpatterns = router.urls
