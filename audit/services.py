import json

from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

from audit.models import AuditLog


def log_event(*, action: str, app_label: str, model: str, object_id: str, payload=None, actor=None):
    normalized_payload = json.loads(json.dumps(payload or {}, cls=DjangoJSONEncoder))
    return AuditLog.objects.create(
        action=action,
        app_label=app_label,
        model=model,
        object_id=str(object_id),
        payload=normalized_payload,
        actor=actor,
    )


def log_model_event(*, instance, action: str, actor=None):
    return log_event(
        action=action,
        app_label=instance._meta.app_label,
        model=instance._meta.model_name,
        object_id=instance.pk,
        payload=model_to_dict(instance),
        actor=actor,
    )
