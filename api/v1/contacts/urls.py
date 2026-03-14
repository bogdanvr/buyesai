from rest_framework.routers import DefaultRouter

from api.v1.contacts.views import ContactViewSet

router = DefaultRouter()
router.register("", ContactViewSet, basename="contacts")

urlpatterns = router.urls
