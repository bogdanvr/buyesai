from rest_framework.routers import DefaultRouter

from api.v1.leads.views import LeadViewSet

router = DefaultRouter()
router.register("", LeadViewSet, basename="leads")

urlpatterns = router.urls
