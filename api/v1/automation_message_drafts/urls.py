from rest_framework.routers import DefaultRouter

from api.v1.automation_message_drafts.views import AutomationMessageDraftViewSet

router = DefaultRouter()
router.register("", AutomationMessageDraftViewSet, basename="automation-message-drafts")

urlpatterns = router.urls
