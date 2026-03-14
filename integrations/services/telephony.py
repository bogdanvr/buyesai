import logging


logger = logging.getLogger(__name__)


def handle_incoming_call_event(payload: dict) -> dict:
    logger.info("Telephony event received: %s", payload.get("event"))
    return {"ok": True, "provider": "telephony"}
