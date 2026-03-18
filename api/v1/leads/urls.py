from rest_framework.routers import DefaultRouter

from django.urls import path

from api.v1.leads.views import LeadAcceptByEmailAPIView, LeadViewSet

router = DefaultRouter()
router.register("", LeadViewSet, basename="leads")

urlpatterns = [
    path("accept/", LeadAcceptByEmailAPIView.as_view(), name="leads-accept"),
    *router.urls,
]
