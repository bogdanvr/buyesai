from rest_framework.routers import DefaultRouter

from api.v1.communications.views import ConversationViewSet, DeliveryFailureQueueViewSet, MessageViewSet

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="communications-conversations")
router.register("messages", MessageViewSet, basename="communications-messages")
router.register("failures", DeliveryFailureQueueViewSet, basename="communications-failures")

urlpatterns = router.urls
