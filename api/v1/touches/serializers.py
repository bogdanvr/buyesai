from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from django.urls import reverse

from crm.models import ClientDocument, DealDocument, Touch
from crm.models.activity import ActivityType, TaskStatus
from crm.models.touch import normalize_touch_channel_code
from crm.services.automation import resolve_touch_automation_rule, should_auto_create_touch_follow_up_task


class TouchSerializer(serializers.ModelSerializer):
    has_follow_up_task = serializers.BooleanField(write_only=True, required=False, default=False)
    deal_document_ids = serializers.PrimaryKeyRelatedField(
        source="deal_documents",
        queryset=DealDocument.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )
    client_document_ids = serializers.PrimaryKeyRelatedField(
        source="client_documents",
        queryset=ClientDocument.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    result_option_name = serializers.CharField(source="result_option.name", read_only=True)
    result_option_code = serializers.CharField(source="result_option.code", read_only=True)
    result_option_group = serializers.CharField(source="result_option.group", read_only=True)
    result_option_class = serializers.CharField(source="result_option.result_class", read_only=True)
    owner_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    task_subject = serializers.CharField(source="task.subject", read_only=True)
    company_name = serializers.SerializerMethodField()
    direction_label = serializers.CharField(source="get_direction_display", read_only=True)
    deal_documents = serializers.SerializerMethodField()
    client_documents = serializers.SerializerMethodField()

    def _document_payload(self, document, scope):
        request = self.context.get("request")
        if scope == "deal":
            relative_url = reverse("deal-documents-download", kwargs={"pk": document.pk})
        else:
            relative_url = reverse("client-documents-download", kwargs={"pk": document.pk})
        try:
            file_size = int(document.file.size or 0)
        except Exception:
            file_size = 0
        uploaded_by = getattr(document, "uploaded_by", None)
        full_name = uploaded_by.get_full_name() if uploaded_by and hasattr(uploaded_by, "get_full_name") else ""
        return {
            "id": document.pk,
            "scope": scope,
            "original_name": str(document.original_name or "").strip() or document.file.name.rsplit("/", 1)[-1],
            "download_url": request.build_absolute_uri(relative_url) if request is not None else relative_url,
            "file_size": file_size,
            "uploaded_by_name": str(full_name or getattr(uploaded_by, "username", "") or "").strip(),
        }

    def get_owner_name(self, obj):
        owner = obj.owner
        if owner is None:
            return ""
        full_name = owner.get_full_name() if hasattr(owner, "get_full_name") else ""
        return str(full_name or getattr(owner, "username", "") or "").strip()

    def get_company_name(self, obj):
        if obj.client_id:
            return str(getattr(obj.client, "name", "") or "").strip()
        if obj.deal_id and getattr(obj.deal, "client", None):
            return str(obj.deal.client.name or "").strip()
        if obj.lead_id:
            if getattr(obj.lead, "client", None):
                return str(obj.lead.client.name or "").strip()
            return str(getattr(obj.lead, "company", "") or "").strip()
        if obj.contact_id and getattr(obj.contact, "client", None):
            return str(obj.contact.client.name or "").strip()
        return ""

    def get_contact_name(self, obj):
        contact = obj.contact
        if contact is None:
            return ""
        return f"{contact.first_name} {contact.last_name}".strip() or contact.phone or f"Контакт #{contact.pk}"

    def get_deal_documents(self, obj):
        return [self._document_payload(document, "deal") for document in obj.deal_documents.all()]

    def get_client_documents(self, obj):
        return [self._document_payload(document, "company") for document in obj.client_documents.all()]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        has_follow_up_task = bool(attrs.pop("has_follow_up_task", False))
        deal_documents = list(attrs.get("deal_documents", []))
        client_documents = list(attrs.get("client_documents", []))
        lead = attrs.get("lead", getattr(self.instance, "lead", None))
        deal = attrs.get("deal", getattr(self.instance, "deal", None))
        client = attrs.get("client", getattr(self.instance, "client", None))
        contact = attrs.get("contact", getattr(self.instance, "contact", None))
        task = attrs.get("task", getattr(self.instance, "task", None))
        happened_at = attrs.get("happened_at", getattr(self.instance, "happened_at", None))
        channel = attrs.get("channel", getattr(self.instance, "channel", None))
        result_option = attrs.get("result_option", getattr(self.instance, "result_option", None))
        if not happened_at:
            raise serializers.ValidationError({"happened_at": "Укажите дату и время касания."})
        if lead is None and deal is None and client is None and contact is None and task is None:
            raise serializers.ValidationError({"lead": "Привяжите касание хотя бы к одному объекту CRM."})
        self._validate_task_link(task, deal, client)
        self._validate_result_option_channel(result_option, channel)
        self._validate_documents(deal_documents, client_documents, deal, client)
        if deal is not None:
            self._validate_deal_next_activity(attrs, deal, has_follow_up_task)
        return attrs

    def _validate_documents(self, deal_documents, client_documents, deal, client):
        if deal_documents:
            if deal is None:
                raise serializers.ValidationError({"deal_document_ids": "Документы сделки можно выбрать только при выбранной сделке."})
            invalid_deal_documents = [document.pk for document in deal_documents if document.deal_id != deal.pk]
            if invalid_deal_documents:
                raise serializers.ValidationError({"deal_document_ids": "Выбран документ другой сделки."})
        resolved_client = client or getattr(deal, "client", None)
        if client_documents:
            if resolved_client is None:
                raise serializers.ValidationError({"client_document_ids": "Документы компании можно выбрать только при выбранной компании."})
            invalid_client_documents = [document.pk for document in client_documents if document.client_id != resolved_client.pk]
            if invalid_client_documents:
                raise serializers.ValidationError({"client_document_ids": "Выбран документ другой компании."})

    def _validate_task_link(self, task, deal, client):
        if task is None:
            return
        if task.type != ActivityType.TASK:
            raise serializers.ValidationError({"task": "Можно выбрать только задачу."})
        if deal is not None:
            if task.deal_id != deal.pk:
                raise serializers.ValidationError({"task": "Можно выбрать только задачу выбранной сделки."})
            return
        if client is not None:
            task_client_id = task.client_id or getattr(getattr(task, "deal", None), "client_id", None)
            if task_client_id != client.pk:
                raise serializers.ValidationError({"task": "Можно выбрать только задачу выбранной компании."})

    def _close_related_task(self, instance):
        task = getattr(instance, "task", None)
        if task is None or task.type != ActivityType.TASK:
            return
        result_text = str(getattr(instance, "summary", "") or "").strip()
        update_fields = []
        if task.status != TaskStatus.DONE:
            task.status = TaskStatus.DONE
            task.is_done = True
            update_fields.extend(["status", "is_done"])
        if result_text and str(task.result or "").strip() != result_text:
            task.result = result_text
            update_fields.append("result")
        completed_at = getattr(instance, "happened_at", None) or timezone.now()
        if task.completed_at != completed_at:
            task.completed_at = completed_at
            update_fields.append("completed_at")
        if update_fields:
            task.save(update_fields=[*update_fields, "updated_at"])

    def create(self, validated_data):
        deal_documents = validated_data.pop("deal_documents", [])
        client_documents = validated_data.pop("client_documents", [])
        with transaction.atomic():
            instance = super().create(validated_data)
            if deal_documents:
                instance.deal_documents.set(deal_documents)
            if client_documents:
                instance.client_documents.set(client_documents)
            self._close_related_task(instance)
        return instance

    def update(self, instance, validated_data):
        deal_documents = validated_data.pop("deal_documents", None)
        client_documents = validated_data.pop("client_documents", None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if deal_documents is not None:
                instance.deal_documents.set(deal_documents)
            if client_documents is not None:
                instance.client_documents.set(client_documents)
            self._close_related_task(instance)
        return instance

    def _validate_result_option_channel(self, result_option, channel):
        return

    def _matched_touch_automation_rule(self, attrs):
        touch_like = Touch(
            channel=attrs.get("channel", getattr(self.instance, "channel", None)),
            result_option=attrs.get("result_option", getattr(self.instance, "result_option", None)),
            direction=attrs.get("direction", getattr(self.instance, "direction", None)),
        )
        _, rule = resolve_touch_automation_rule(touch_like)
        return rule

    def _allows_automatic_follow_up_task(self, attrs) -> bool:
        rule = self._matched_touch_automation_rule(attrs)
        touch_like = Touch(
            channel=attrs.get("channel", getattr(self.instance, "channel", None)),
            result_option=attrs.get("result_option", getattr(self.instance, "result_option", None)),
            direction=attrs.get("direction", getattr(self.instance, "direction", None)),
        )
        return should_auto_create_touch_follow_up_task(touch_like, rule)

    def _validate_deal_next_activity(self, attrs, deal, has_follow_up_task=False):
        stage_code = str(getattr(getattr(deal, "stage", None), "code", "") or "").strip().lower()
        if stage_code in {"won", "failed", "lost"}:
            return
        if has_follow_up_task:
            return
        if self._allows_automatic_follow_up_task(attrs):
            return

        now = timezone.now()
        next_step_at = attrs.get("next_step_at", getattr(self.instance, "next_step_at", None))
        if next_step_at and next_step_at >= now:
            return

        has_future_touch = deal.touches.filter(next_step_at__gte=now)
        if self.instance is not None and self.instance.pk:
            has_future_touch = has_future_touch.exclude(pk=self.instance.pk)
        if has_future_touch.exists():
            return

        has_active_task = deal.activities.filter(
            type=ActivityType.TASK,
            status__in={TaskStatus.TODO, TaskStatus.IN_PROGRESS},
            due_at__gte=now,
        ).exists()
        if has_active_task:
            return

        raise serializers.ValidationError(
            {
                "next_step_at": (
                    "После касания по активной сделке должна остаться следующая активность: "
                    "укажите дату следующего шага, создайте задачу или закройте сделку."
                )
            }
        )

    class Meta:
        model = Touch
        fields = [
            "id",
            "happened_at",
            "channel",
            "channel_name",
            "result_option",
            "result_option_name",
            "result_option_code",
            "result_option_group",
            "result_option_class",
            "direction",
            "direction_label",
            "summary",
            "next_step",
            "next_step_at",
            "owner",
            "owner_name",
            "contact",
            "contact_name",
            "lead",
            "lead_title",
            "deal",
            "deal_title",
            "client",
            "client_name",
            "task",
            "task_subject",
            "company_name",
            "created_at",
            "updated_at",
            "has_follow_up_task",
            "deal_document_ids",
            "client_document_ids",
            "deal_documents",
            "client_documents",
        ]
        read_only_fields = ("created_at", "updated_at")
