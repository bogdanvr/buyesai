from django.utils import timezone

from integrations.models import IntegrationWebhookEvent
from integrations.services.email import handle_email_event
from integrations.services.telephony import handle_incoming_call_event
from integrations.services.telegram import handle_telegram_event


HANDLERS = {
    "telephony": handle_incoming_call_event,
    "telegram": handle_telegram_event,
    "email": handle_email_event,
}


def store_webhook_event(*, source: str, event_type: str, payload: dict, external_id: str = ""):
    return IntegrationWebhookEvent.objects.create(
        source=source,
        event_type=event_type,
        external_id=external_id,
        payload=payload,
    )


def process_webhook_event(event: IntegrationWebhookEvent) -> dict:
    handler = HANDLERS.get(event.source)
    if handler is None:
        event.process_error = f"Unsupported source: {event.source}"
        event.save(update_fields=["process_error"])
        return {"ok": False, "error": event.process_error}

    result = handler(event.payload or {})
    event.is_processed = True
    event.processed_at = timezone.now()
    event.process_error = ""
    event.save(update_fields=["is_processed", "processed_at", "process_error"])
    return result
