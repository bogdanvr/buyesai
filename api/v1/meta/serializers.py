from rest_framework import serializers
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from crm.models import (
    AutomationRule,
    CommunicationChannel,
    ContactRole,
    ContactStatus,
    DealStage,
    LeadSource,
    LeadStatus,
    NextStepTemplate,
    OutcomeCatalog,
    TaskCategory,
    TaskType,
    TouchResult,
)


User = get_user_model()


class LeadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStatus
        fields = ["id", "name", "code", "order", "is_active", "is_final"]


class DealStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealStage
        fields = ["id", "name", "code", "order", "is_active", "is_final"]


class LeadSourceSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise serializers.ValidationError("Название источника обязательно.")
        return normalized

    def create(self, validated_data):
        name = validated_data["name"]
        base_code = slugify(name, allow_unicode=False).replace("-", "_") or "source"
        code = base_code
        index = 2
        while LeadSource.objects.filter(code=code).exists():
            code = f"{base_code}_{index}"
            index += 1
        validated_data["code"] = code
        validated_data.setdefault("is_active", True)
        return super().create(validated_data)

    class Meta:
        model = LeadSource
        fields = ["id", "name", "code", "description", "is_active"]
        read_only_fields = ("code",)


class CommunicationChannelSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()

    def get_code(self, obj):
        return slugify(str(getattr(obj, "name", "") or "").strip(), allow_unicode=False).replace("-", "_")

    class Meta:
        model = CommunicationChannel
        fields = ["id", "name", "code", "is_active"]


class ContactRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactRole
        fields = ["id", "name", "is_active"]


class ContactStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactStatus
        fields = ["id", "name", "is_active"]


class UserOptionSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        full_name = obj.get_full_name() if hasattr(obj, "get_full_name") else ""
        return str(full_name or getattr(obj, "username", "") or "").strip()

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name"]


class TaskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = [
            "id",
            "name",
            "code",
            "sort_order",
            "uses_communication_channel",
            "requires_follow_up_task_on_done",
            "satisfies_deal_next_step_requirement",
            "is_active",
        ]


class TaskTypeSerializer(serializers.ModelSerializer):
    auto_task_type_name = serializers.CharField(source="auto_task_type.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_uses_communication_channel = serializers.BooleanField(source="category.uses_communication_channel", read_only=True)
    category_requires_follow_up_task_on_done = serializers.BooleanField(source="category.requires_follow_up_task_on_done", read_only=True)
    category_satisfies_deal_next_step_requirement = serializers.BooleanField(source="category.satisfies_deal_next_step_requirement", read_only=True)

    class Meta:
        model = TaskType
        fields = [
            "id",
            "name",
            "sort_order",
            "category",
            "category_name",
            "category_uses_communication_channel",
            "category_requires_follow_up_task_on_done",
            "category_satisfies_deal_next_step_requirement",
            "auto_touch_on_done",
            "touch_result",
            "auto_task_on_done",
            "auto_task_type",
            "auto_task_type_name",
            "is_active",
        ]


class TouchResultSerializer(serializers.ModelSerializer):
    group_label = serializers.SerializerMethodField()
    result_class = serializers.CharField(read_only=True)
    result_class_label = serializers.SerializerMethodField()

    def get_group_label(self, obj):
        return str(getattr(obj, "group", "") or "").strip()

    def get_result_class_label(self, obj):
        return str(getattr(obj, "result_class", "") or "").strip()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["class"] = data.pop("result_class", "")
        return data

    class Meta:
        model = TouchResult
        fields = [
            "id",
            "code",
            "name",
            "group",
            "group_label",
            "result_class",
            "result_class_label",
            "requires_next_step",
            "requires_loss_reason",
            "is_active",
            "sort_order",
            "allowed_touch_types",
        ]


class OutcomeCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutcomeCatalog
        fields = ["id", "code", "name"]


class NextStepTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NextStepTemplate
        fields = ["id", "code", "name"]


class AutomationRuleSerializer(serializers.ModelSerializer):
    default_outcome_code = serializers.CharField(source="default_outcome.code", read_only=True)
    default_outcome_name = serializers.CharField(source="default_outcome.name", read_only=True)
    next_step_template_code = serializers.CharField(source="next_step_template.code", read_only=True)
    next_step_template_name = serializers.CharField(source="next_step_template.name", read_only=True)

    class Meta:
        model = AutomationRule
        fields = [
            "id",
            "event_type",
            "ui_mode",
            "ui_priority",
            "write_timeline",
            "show_in_summary",
            "show_in_attention_queue",
            "merge_key",
            "auto_open_panel",
            "create_message",
            "create_touchpoint_mode",
            "default_outcome",
            "default_outcome_code",
            "default_outcome_name",
            "allow_auto_create_task",
            "require_manager_confirmation",
            "next_step_template",
            "next_step_template_code",
            "next_step_template_name",
            "is_active",
            "sort_order",
        ]
