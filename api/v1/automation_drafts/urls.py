from rest_framework.routers import DefaultRouter

from api.v1.automation_drafts.views import AutomationDraftViewSet

router = DefaultRouter()
router.register("", AutomationDraftViewSet, basename="automation-drafts")

urlpatterns = router.urls
