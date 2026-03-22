from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.v1.communications.serializers import (
    ConversationBindSerializer,
    ConversationSendSerializer,
    ConversationStartSerializer,
    ConversationSerializer,
    DeliveryFailureQueueSerializer,
    DeliveryFailureResolutionSerializer,
    DeliveryFailureRetrySerializer,
    MessageAttemptLogSerializer,
    MessageSerializer,
)
from crm.models import Client, Contact, Deal
from crm_communications.email_outbound import EmailOutboundMessageService
from crm_communications.models import Conversation, ConversationRoute, DeliveryFailureQueue, Message, MessageAttemptLog
from crm_communications.services import ConversationBindingService, MessageQueueService, TelegramOutboundMessageService, normalize_telegram_key


def dispatch_outgoing_message(*, message: Message) -> Message:
    if message.channel == "telegram":
        return TelegramOutboundMessageService.send_message(message=message)
    if message.channel == "email":
        return EmailOutboundMessageService.send_message(message=message)
    raise ValueError(f"Канал {message.channel} не поддерживается.")


def sync_message_context_from_conversation(*, message: Message) -> Message:
    conversation = message.conversation
    message.client = conversation.client
    message.contact = conversation.contact
    message.deal = conversation.deal
    message.save(update_fields=["client", "contact", "deal", "updated_at"])
    if message.touch_id:
        touch = message.touch
        touch.client = conversation.client
        touch.contact = conversation.contact
        touch.deal = conversation.deal
        touch.lead = getattr(conversation.deal, "lead", None)
        touch.save(update_fields=["client", "contact", "deal", "lead", "updated_at"])
    return message


def sync_conversation_message_contexts_from_conversation(*, conversation: Conversation) -> None:
    for message in conversation.messages.select_related("touch", "deal").all():
        sync_message_context_from_conversation(message=message)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        queryset = Conversation.objects.select_related(
            "client",
            "contact",
            "deal",
            "last_message",
        ).prefetch_related("routes").order_by("-last_message_at", "-id")
        client_id = self.request.query_params.get("client")
        deal_id = self.request.query_params.get("deal")
        channel = self.request.query_params.get("channel")
        requires_manual_binding = self.request.query_params.get("requires_manual_binding")
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if channel:
            queryset = queryset.filter(channel=channel)
        if requires_manual_binding in {"true", "false"}:
            queryset = queryset.filter(requires_manual_binding=requires_manual_binding == "true")
        return queryset

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        queryset = conversation.messages.select_related("client", "contact", "deal", "author_user").prefetch_related("attachments").order_by("created_at", "id")
        serializer = MessageSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def bind(self, request, pk=None):
        conversation = self.get_object()
        serializer = ConversationBindSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = Client.objects.filter(pk=data.get("client")).first() if "client" in data else conversation.client
        contact = Contact.objects.filter(pk=data.get("contact")).first() if "contact" in data else conversation.contact
        deal = Deal.objects.filter(pk=data.get("deal")).first() if "deal" in data else conversation.deal

        primary_route = conversation.routes.order_by("-is_primary", "-id").first()
        route_type = str(data.get("route_type") or getattr(primary_route, "route_type", "") or "").strip()
        route_key = str(data.get("route_key") or getattr(primary_route, "route_key", "") or "").strip()
        if not route_type or not route_key:
            return Response({"detail": "Не найден маршрут диалога для ручной привязки."}, status=status.HTTP_400_BAD_REQUEST)

        ConversationBindingService.bind_conversation(
            conversation=conversation,
            channel=conversation.channel,
            route_type=route_type,
            route_key=route_key,
            client=client,
            contact=contact,
            deal=deal,
            resolved_by=request.user if request.user.is_authenticated else None,
            resolution_source="api_manual_bind",
        )
        conversation.refresh_from_db()
        sync_conversation_message_contexts_from_conversation(conversation=conversation)
        return Response(ConversationSerializer(conversation, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        conversation = self.get_object()
        serializer = ConversationSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        message = Message.objects.create(
            conversation=conversation,
            channel=conversation.channel,
            direction="outgoing",
            status="draft",
            client=conversation.client,
            contact=conversation.contact,
            deal=conversation.deal,
            author_user=request.user if request.user.is_authenticated else None,
            subject=str(payload.get("subject") or "").strip(),
            body_text=str(payload.get("body_text") or "").strip(),
            body_html=str(payload.get("body_html") or "").strip(),
            body_preview=str(payload.get("body_text") or payload.get("subject") or "").strip()[:500],
            external_recipient_key=str(payload.get("recipient") or "").strip(),
        )
        MessageQueueService.enqueue_message(message=message)
        try:
            message = dispatch_outgoing_message(message=message)
        except ValueError as exc:
            return Response({"detail": f"Канал {conversation.channel} не поддерживается."}, status=status.HTTP_400_BAD_REQUEST)

        message.refresh_from_db()
        return Response(MessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def start(self, request):
        serializer = ConversationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        deal = Deal.objects.filter(pk=payload.get("deal")).select_related("client").first() if payload.get("deal") else None
        client = Client.objects.filter(pk=payload.get("client")).first() if payload.get("client") else getattr(deal, "client", None)
        contact = Contact.objects.filter(pk=payload.get("contact")).first() if payload.get("contact") else None
        channel = str(payload.get("channel") or "").strip()
        recipient = str(payload.get("recipient") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        body_text = str(payload.get("body_text") or "").strip()
        body_html = str(payload.get("body_html") or "").strip()

        conversation = Conversation.objects.create(
            channel=channel,
            subject=subject or getattr(deal, "title", "") or "Новый диалог",
            client=client,
            contact=contact,
            deal=deal,
            status="active",
            requires_manual_binding=False,
        )
        if channel == "telegram" and recipient:
            chat_id = recipient.removeprefix("telegram:").strip()
            if chat_id.isdigit():
                ConversationBindingService.bind_conversation(
                    conversation=conversation,
                    channel=channel,
                    route_type="telegram_chat",
                    route_key=chat_id,
                    client=client,
                    contact=contact,
                    deal=deal,
                    resolved_by=request.user if request.user.is_authenticated else None,
                    resolution_source="api_start_conversation",
                )
                if contact or client:
                    ConversationBindingService.ensure_participant_binding(
                        channel=channel,
                        external_participant_key=normalize_telegram_key(chat_id),
                        client=client,
                        contact=contact,
                        external_display_name="",
                    )

        message = Message.objects.create(
            conversation=conversation,
            channel=channel,
            direction="outgoing",
            status="draft",
            client=client,
            contact=contact,
            deal=deal,
            author_user=request.user if request.user.is_authenticated else None,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            body_preview=str(body_text or subject or "").strip()[:500],
            external_recipient_key=recipient,
        )
        MessageQueueService.enqueue_message(message=message)
        try:
            message = dispatch_outgoing_message(message=message)
        except ValueError:
            return Response({"detail": f"Канал {channel} не поддерживается."}, status=status.HTTP_400_BAD_REQUEST)

        conversation.refresh_from_db()
        message.refresh_from_db()
        return Response(
            {
                "conversation": ConversationSerializer(conversation, context={"request": request}).data,
                "message": MessageSerializer(message, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageSerializer

    def get_queryset(self):
        queryset = Message.objects.select_related(
            "conversation",
            "client",
            "contact",
            "deal",
            "author_user",
        ).prefetch_related("attachments").order_by("-created_at", "-id")
        conversation_id = self.request.query_params.get("conversation")
        status_code = self.request.query_params.get("status")
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        if status_code:
            queryset = queryset.filter(status=status_code)
        return queryset

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        message = self.get_object()
        if message.direction != "outgoing":
            return Response({"detail": "Повтор доступен только для исходящих сообщений."}, status=status.HTTP_400_BAD_REQUEST)
        if message.status not in {"failed", "requires_manual_retry"}:
            return Response({"detail": "Повтор доступен только для failed/requires_manual_retry."}, status=status.HTTP_400_BAD_REQUEST)

        MessageQueueService.enqueue_message(message=message, force=True)
        try:
            message = dispatch_outgoing_message(message=message)
        except ValueError as exc:
            return Response({"detail": f"Канал {message.channel} не поддерживается."}, status=status.HTTP_400_BAD_REQUEST)
        message.refresh_from_db()
        return Response(MessageSerializer(message, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def attempts(self, request, pk=None):
        message = self.get_object()
        queryset = message.attempt_logs.order_by("-attempt_number", "-id")
        serializer = MessageAttemptLogSerializer(queryset, many=True)
        return Response(serializer.data)


class DeliveryFailureQueueViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DeliveryFailureQueueSerializer

    def get_queryset(self):
        queryset = DeliveryFailureQueue.objects.select_related(
            "assigned_to",
            "last_attempt_log",
            "message",
            "message__conversation",
            "message__client",
            "message__contact",
            "message__deal",
        ).order_by("-created_at", "-id")
        resolution_status = self.request.query_params.get("resolution_status")
        if resolution_status:
            queryset = queryset.filter(resolution_status=resolution_status)
        elif getattr(self, "action", "") == "list":
            queryset = queryset.exclude(resolution_status="resolved").exclude(resolution_status="closed")
        return queryset

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        failure_item = self.get_object()
        serializer = DeliveryFailureRetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = failure_item.message
        if message.direction != "outgoing":
            return Response({"detail": "Повтор доступен только для исходящих сообщений."}, status=status.HTTP_400_BAD_REQUEST)

        recipient = str(serializer.validated_data.get("recipient") or "").strip()
        if recipient:
            message.external_recipient_key = recipient
            message.save(update_fields=["external_recipient_key", "updated_at"])

        if request.user.is_authenticated:
            failure_item.assigned_to = request.user
        failure_item.resolution_status = "in_progress"
        failure_item.resolution_comment = ""
        failure_item.resolved_at = None
        failure_item.save(update_fields=["assigned_to", "resolution_status", "resolution_comment", "resolved_at", "updated_at"])

        MessageQueueService.enqueue_message(message=message, force=True)
        try:
            message = dispatch_outgoing_message(message=message)
        except ValueError:
            return Response({"detail": f"Канал {message.channel} не поддерживается."}, status=status.HTTP_400_BAD_REQUEST)
        failure_item.refresh_from_db()
        message.refresh_from_db()
        return Response(
            {
                "failure": DeliveryFailureQueueSerializer(failure_item, context={"request": request}).data,
                "message": MessageSerializer(message, context={"request": request}).data,
            }
        )

    @action(detail=True, methods=["post"])
    def bind(self, request, pk=None):
        failure_item = self.get_object()
        serializer = ConversationBindSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        message = failure_item.message
        conversation = message.conversation
        client = Client.objects.filter(pk=data.get("client")).first() if "client" in data else conversation.client
        contact = Contact.objects.filter(pk=data.get("contact")).first() if "contact" in data else conversation.contact
        deal = Deal.objects.filter(pk=data.get("deal")).first() if "deal" in data else conversation.deal

        primary_route = conversation.routes.order_by("-is_primary", "-id").first()
        route_type = str(data.get("route_type") or getattr(primary_route, "route_type", "") or "").strip()
        route_key = str(data.get("route_key") or getattr(primary_route, "route_key", "") or "").strip()
        if not route_type or not route_key:
            return Response({"detail": "Не найден маршрут диалога для перепривязки."}, status=status.HTTP_400_BAD_REQUEST)

        ConversationBindingService.bind_conversation(
            conversation=conversation,
            channel=conversation.channel,
            route_type=route_type,
            route_key=route_key,
            client=client,
            contact=contact,
            deal=deal,
            resolved_by=request.user if request.user.is_authenticated else None,
            resolution_source="api_failure_bind",
        )
        conversation.refresh_from_db()
        sync_conversation_message_contexts_from_conversation(conversation=conversation)

        if request.user.is_authenticated:
            failure_item.assigned_to = request.user
        failure_item.resolution_status = "in_progress"
        failure_item.resolved_at = None
        failure_item.save(update_fields=["assigned_to", "resolution_status", "resolved_at", "updated_at"])
        failure_item.refresh_from_db()
        message.refresh_from_db()
        return Response(
            {
                "failure": DeliveryFailureQueueSerializer(failure_item, context={"request": request}).data,
                "conversation": ConversationSerializer(conversation, context={"request": request}).data,
                "message": MessageSerializer(message, context={"request": request}).data,
            }
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        failure_item = self.get_object()
        serializer = DeliveryFailureResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failure_item.resolution_status = "resolved"
        failure_item.resolved_at = timezone.now()
        failure_item.resolution_comment = str(serializer.validated_data.get("resolution_comment") or "").strip()
        if request.user.is_authenticated:
            failure_item.assigned_to = request.user
        failure_item.save(update_fields=["resolution_status", "resolved_at", "resolution_comment", "assigned_to", "updated_at"])
        return Response(DeliveryFailureQueueSerializer(failure_item, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        failure_item = self.get_object()
        serializer = DeliveryFailureResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failure_item.resolution_status = "closed"
        failure_item.resolved_at = timezone.now()
        failure_item.resolution_comment = str(serializer.validated_data.get("resolution_comment") or "").strip()
        if request.user.is_authenticated:
            failure_item.assigned_to = request.user
        failure_item.save(update_fields=["resolution_status", "resolved_at", "resolution_comment", "assigned_to", "updated_at"])
        return Response(DeliveryFailureQueueSerializer(failure_item, context={"request": request}).data)
