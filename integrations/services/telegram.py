import logging


logger = logging.getLogger(__name__)


def handle_telegram_event(payload: dict) -> dict:
    logger.info("Telegram event received: %s", payload.get("update_id"))
    return {"ok": True, "provider": "telegram"}
