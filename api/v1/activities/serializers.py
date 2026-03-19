from rest_framework import serializers
from django.utils import timezone

from crm.models import Activity
from crm.models.activity import ActivityType, TaskStatus, TaskTypeGroup


class ActivitySerializer(serializers.ModelSerializer):
    subject = serializers.CharField(required=False, allow_blank=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    deal_title = serializers.CharField(source="deal.title", read_only=True)
    contact_name = serializers.SerializerMethodField()
    task_type_name = serializers.CharField(source="task_type.name", read_only=True)
    task_type_group = serializers.CharField(source="task_type.group", read_only=True)
    task_type_group_label = serializers.CharField(source="task_type.get_group_display", read_only=True)
    communication_channel_name = serializers.CharField(source="communication_channel.name", read_only=True)
    related_touch_subject = serializers.CharField(source="related_touch.subject", read_only=True)
    status_label = serializers.SerializerMethodField()
    has_follow_up_task = serializers.BooleanField(write_only=True, required=False, default=False)

    ACTIVE_TASK_STATUSES = {TaskStatus.TODO, TaskStatus.IN_PROGRESS}

    def _has_automatic_follow_up_task(self, task_type):
        if task_type is None:
            return False
        return bool(getattr(task_type, "auto_task_on_done", False) and getattr(task_type, "auto_task_type_id", None))

    def _has_non_overdue_client_task_for_deal(self, deal, current_task_id=None):
        if deal is None:
            return False
        now = timezone.now()
        queryset = deal.activities.filter(
            type=ActivityType.TASK,
            status__in=self.ACTIVE_TASK_STATUSES,
            task_type__group=TaskTypeGroup.CLIENT_TASK,
            due_at__gte=now,
        )
        if current_task_id is not None:
            queryset = queryset.exclude(pk=current_task_id)
        return queryset.exists()

    def get_status_label(self, obj):
        if obj.type != ActivityType.TASK:
            return ""
        return obj.get_status_display()

    def _resolve_task_status(self, attrs):
        if "status" in attrs:
            return attrs["status"]
        if "is_done" in attrs:
            return TaskStatus.DONE if attrs["is_done"] else TaskStatus.TODO
        if self.instance is not None:
            return getattr(self.instance, "status", TaskStatus.TODO)
        return TaskStatus.TODO

    def get_contact_name(self, obj):
        contact = obj.contact
        if contact is None:
            return ""
        full_name = f"{contact.first_name} {contact.last_name}".strip()
        return full_name or contact.phone or f"Контакт #{contact.id}"

    def _resolve_task_subject(self, attrs, activity_type, task_type):
        if activity_type != ActivityType.TASK:
            return
        subject = str(attrs.get("subject", getattr(self.instance, "subject", "")) or "").strip()
        if subject:
            attrs["subject"] = subject
            return
        task_type_name = str(getattr(task_type, "name", "") or "").strip()
        if task_type_name:
            attrs["subject"] = task_type_name
            return
        raise serializers.ValidationError({"subject": "Укажите название задачи или выберите тип задачи."})

    def _resolve_task_result(self, attrs, activity_type, task_type):
        if activity_type != ActivityType.TASK:
            return ""
        result = str(attrs.get("result", getattr(self.instance, "result", "")) or "").strip()
        if result:
            attrs["result"] = result
            return result
        task_type_result = str(getattr(task_type, "touch_result", "") or "").strip()
        if task_type_result:
            attrs["result"] = task_type_result
            return task_type_result
        attrs["result"] = ""
        return ""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        activity_type = attrs.get("type", getattr(self.instance, "type", None))
        due_at = attrs.get("due_at", getattr(self.instance, "due_at", None))
        status = self._resolve_task_status(attrs)
        is_done = status == TaskStatus.DONE
        task_type = attrs.get("task_type", getattr(self.instance, "task_type", None))
        task_type_group = str(getattr(task_type, "group", "") or "").strip()
        has_automatic_follow_up_task = self._has_automatic_follow_up_task(task_type)
        communication_channel = attrs.get(
            "communication_channel",
            getattr(self.instance, "communication_channel", None),
        )
        deal = attrs.get("deal", getattr(self.instance, "deal", None))
        related_touch = attrs.get("related_touch", getattr(self.instance, "related_touch", None))
        has_follow_up_task = bool(attrs.pop("has_follow_up_task", False))
        save_company_note = attrs.get(
            "save_company_note",
            getattr(self.instance, "save_company_note", False),
        )
        company_note = attrs.get("company_note", getattr(self.instance, "company_note", ""))
        self._resolve_task_subject(attrs, activity_type, task_type)
        result = self._resolve_task_result(attrs, activity_type, task_type)
        if activity_type == ActivityType.TASK:
            attrs["status"] = status
            attrs["is_done"] = is_done
            if task_type_group != TaskTypeGroup.CLIENT_TASK and communication_channel is not None:
                attrs["communication_channel"] = None
        if activity_type == ActivityType.TASK and not due_at:
            raise serializers.ValidationError({"due_at": "Укажите срок задачи."})
        if activity_type == ActivityType.TASK and related_touch is not None:
            if self.instance is not None and related_touch.pk == self.instance.pk:
                raise serializers.ValidationError({"related_touch": "Нельзя связать задачу саму с собой."})
            if related_touch.type == ActivityType.TASK:
                raise serializers.ValidationError({"related_touch": "Связанное касание должно быть активностью, а не задачей."})
        if activity_type == ActivityType.TASK and is_done:
            has_result = bool(str(result or "").strip())
            has_non_overdue_client_task = self._has_non_overdue_client_task_for_deal(
                deal,
                current_task_id=getattr(self.instance, "pk", None),
            )
            if task_type_group == TaskTypeGroup.CLIENT_TASK:
                if communication_channel is None:
                    raise serializers.ValidationError(
                        {"communication_channel": "Укажите тип канала перед завершением клиентской задачи."}
                    )
            if not has_result:
                raise serializers.ValidationError(
                    {"result": "Укажите результат выполнения задачи или задайте его в типе задачи."}
                )
        if (
            activity_type == ActivityType.TASK
            and is_done
            and task_type_group == TaskTypeGroup.INTERNAL_TASK
            and not has_follow_up_task
            and not has_automatic_follow_up_task
            and not has_non_overdue_client_task
        ):
            raise serializers.ValidationError(
                {"has_follow_up_task": "Для внутренней задачи заполните следующую задачу перед завершением текущей."}
            )
        if activity_type == ActivityType.TASK and save_company_note and not str(company_note or "").strip():
            raise serializers.ValidationError({"company_note": "Укажите важные факты о компании."})
        if activity_type == ActivityType.TASK and is_done and deal is not None:
            stage_code = str(getattr(getattr(deal, "stage", None), "code", "") or "").strip().lower()
            if stage_code not in {"won", "failed"}:
                if not has_non_overdue_client_task and not has_follow_up_task and not has_automatic_follow_up_task:
                    raise serializers.ValidationError(
                        {"has_follow_up_task": "Для активной сделки укажите следующую задачу или держите актуальную клиентскую задачу без просрочки."}
                    )
        return attrs

    def create(self, validated_data):
        if validated_data.get("status") == TaskStatus.DONE:
            validated_data["completed_at"] = validated_data.get("completed_at") or timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        status = validated_data.get("status", instance.status)
        is_done = status == TaskStatus.DONE
        validated_data["is_done"] = is_done
        if is_done and not instance.completed_at and "completed_at" not in validated_data:
            validated_data["completed_at"] = timezone.now()
        if not is_done and ("status" in validated_data or "is_done" in validated_data):
            validated_data["completed_at"] = None
        return super().update(instance, validated_data)

    class Meta:
        model = Activity
        fields = [
            "id",
            "type",
            "subject",
            "description",
            "result",
            "due_at",
            "status",
            "status_label",
            "priority",
            "task_type",
            "task_type_name",
            "task_type_group",
            "task_type_group_label",
            "communication_channel",
            "communication_channel_name",
            "related_touch",
            "related_touch_subject",
            "deadline_reminder_offset_minutes",
            "completed_at",
            "is_done",
            "has_follow_up_task",
            "save_company_note",
            "company_note",
            "lead",
            "lead_title",
            "deal",
            "deal_title",
            "client",
            "client_name",
            "contact",
            "contact_name",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("completed_at", "created_at", "updated_at")
