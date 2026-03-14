import logging


logger = logging.getLogger(__name__)


def handle_email_event(payload: dict) -> dict:
    logger.info("Email event received: %s", payload.get("message_id"))
    return {"ok": True, "provider": "email"}
