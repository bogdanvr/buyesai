from rest_framework import serializers
from django.utils import timezone

from crm.models import Activity
from crm.models.activity import ActivityType, TaskStatus, TaskTypeGroup


class ActivitySerializer(serializers.ModelSerializer):
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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        activity_type = attrs.get("type", getattr(self.instance, "type", None))
        due_at = attrs.get("due_at", getattr(self.instance, "due_at", None))
        status = self._resolve_task_status(attrs)
        is_done = status == TaskStatus.DONE
        result = attrs.get("result", getattr(self.instance, "result", ""))
        task_type = attrs.get("task_type", getattr(self.instance, "task_type", None))
        task_type_group = str(getattr(task_type, "group", "") or "").strip()
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
            has_related_touch = related_touch is not None
            if task_type_group == TaskTypeGroup.INTERNAL_TASK and not has_result:
                raise serializers.ValidationError({"result": "Для внутренней задачи укажите результат выполнения."})
            if task_type_group == TaskTypeGroup.CLIENT_TASK:
                pass
            elif not has_result and not has_related_touch:
                raise serializers.ValidationError(
                    {"result": "Укажите результат завершения задачи или привяжите касание."}
                )
        if activity_type == ActivityType.TASK and is_done and task_type_group == TaskTypeGroup.INTERNAL_TASK and not has_follow_up_task:
            raise serializers.ValidationError(
                {"has_follow_up_task": "Для внутренней задачи заполните следующую задачу перед завершением текущей."}
            )
        if activity_type == ActivityType.TASK and save_company_note and not str(company_note or "").strip():
            raise serializers.ValidationError({"company_note": "Укажите важные факты о компании."})
        if activity_type == ActivityType.TASK and is_done and deal is not None:
            stage_code = str(getattr(getattr(deal, "stage", None), "code", "") or "").strip().lower()
            if stage_code not in {"won", "failed"}:
                active_tasks_qs = deal.activities.filter(type=ActivityType.TASK, status__in=self.ACTIVE_TASK_STATUSES)
                if self.instance is not None:
                    active_tasks_qs = active_tasks_qs.exclude(pk=self.instance.pk)
                has_other_active_tasks = active_tasks_qs.exists()
                if not has_other_active_tasks and not has_follow_up_task:
                    raise serializers.ValidationError(
                        {"has_follow_up_task": "Для активной сделки укажите следующую задачу перед завершением текущей."}
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
