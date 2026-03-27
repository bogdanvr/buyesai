from integrations.models import TelephonyEventLog
from integrations.novofon.services import (
    create_missed_call_followup_task,
    import_novofon_calls_history,
    process_novofon_webhook_event,
    refresh_call_recording_if_needed,
    sync_novofon_employees,
)


def process_novofon_webhook_event_task(event_id: int):
    event = TelephonyEventLog.objects.filter(pk=event_id).first()
    if event is None:
        return {"ok": False, "error": "event_not_found"}
    return process_novofon_webhook_event(event)


def sync_novofon_employees_task():
    return sync_novofon_employees()


def import_novofon_calls_history_task(**kwargs):
    return import_novofon_calls_history(**kwargs)


def refresh_call_recording_if_needed_task(call):
    return refresh_call_recording_if_needed(call)


def create_missed_call_followup_task_task(call):
    return create_missed_call_followup_task(call)
