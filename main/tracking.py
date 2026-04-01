import hashlib

from django.utils import timezone
from django.utils.text import slugify

from crm.models import LeadSource, TrafficSource
from main.models import WebsiteSession, WebsiteSessionEvent


TRACKING_EVENT_TYPES = {
    "page_view",
    "chat_opened",
    "first_message_sent",
    "form_submitted",
    "phone_clicked",
    "messenger_clicked",
}

DEDUPED_TRACKING_EVENTS = {
    "page_view",
    "chat_opened",
    "first_message_sent",
}

TRACKING_SOURCE_DEFINITIONS = (
    ("utm_source", "traffic-source", "Источник трафика"),
    ("utm_medium", "traffic-medium", "Канал"),
    ("utm_campaign", "traffic-campaign", "Кампания"),
    ("utm_content", "traffic-content", "Объявление"),
    ("utm_term", "traffic-term", "Ключ"),
)

def _clean_text(value) -> str:
    return str(value or "").strip()


def normalize_session_id(value) -> str:
    return _clean_text(value)[:64]


def extract_tracking_session_id(payload: dict | None) -> str:
    if not isinstance(payload, dict):
        return ""
    return normalize_session_id(
        payload.get("session_id")
        or payload.get("tracking_session_id")
        or payload.get("internal_session_id")
    )


def get_or_create_website_session(*, session_id: str, payload: dict | None = None) -> WebsiteSession | None:
    normalized_session_id = normalize_session_id(session_id)
    if not normalized_session_id:
        return None

    session, created = WebsiteSession.objects.get_or_create(session_id=normalized_session_id)
    payload = payload if isinstance(payload, dict) else {}

    update_fields = []
    raw_mappings = {
        "utm_source": _clean_text(payload.get("utm_source")),
        "utm_medium": _clean_text(payload.get("utm_medium")),
        "utm_campaign": _clean_text(payload.get("utm_campaign")),
        "utm_content": _clean_text(payload.get("utm_content")),
        "utm_term": _clean_text(payload.get("utm_term")),
        "yclid": _clean_text(payload.get("yclid")),
        "referer": _clean_text(payload.get("referer")),
        "landing_url": _clean_text(payload.get("landing_url") or payload.get("page_url")),
    }

    for field_name, value in raw_mappings.items():
        if value and getattr(session, field_name) != value and not getattr(session, field_name):
            setattr(session, field_name, value)
            update_fields.append(field_name)

    client_id = _clean_text(payload.get("client_id"))
    if client_id and session.client_id != client_id:
        session.client_id = client_id
        update_fields.append("client_id")

    if update_fields and not created:
        update_fields.append("updated_at")
        session.save(update_fields=update_fields)
    elif created:
        session.save()

    return session


def record_website_event(
    *,
    session: WebsiteSession | None,
    event_type: str,
    page_url: str = "",
    payload: dict | None = None,
) -> WebsiteSessionEvent | None:
    if session is None:
        return None

    normalized_event_type = _clean_text(event_type)
    if normalized_event_type not in TRACKING_EVENT_TYPES:
        return None

    if normalized_event_type in DEDUPED_TRACKING_EVENTS:
        existing = session.events.filter(event_type=normalized_event_type).order_by("id").first()
        if existing is not None:
            return existing

    event_payload = payload if isinstance(payload, dict) else {}
    event = WebsiteSessionEvent.objects.create(
        session=session,
        event_type=normalized_event_type,
        page_url=_clean_text(page_url),
        payload=event_payload,
    )

    if normalized_event_type == "first_message_sent" and not session.first_message_at:
        message = _clean_text(event_payload.get("message") or event_payload.get("text"))
        session.first_message_at = event.created_at or timezone.now()
        session.first_message = message
        session.save(update_fields=["first_message_at", "first_message", "updated_at"])

    sync_lead_tracking_for_session(session)
    return event


def build_lead_history(session: WebsiteSession | None) -> list[dict]:
    if session is None:
        return []

    history = []
    for event in session.events.order_by("created_at", "id"):
        payload = event.payload if isinstance(event.payload, dict) else {}
        history_item = {
            "event": event.event_type,
            "timestamp": timezone.localtime(event.created_at).isoformat() if event.created_at else "",
        }
        form_type = _clean_text(payload.get("form_type"))
        href = _clean_text(payload.get("href"))
        label = _clean_text(payload.get("label"))
        if form_type:
            history_item["form_type"] = form_type
        if href:
            history_item["href"] = href
        if label:
            history_item["label"] = label
        history.append(history_item)
    return history


def _tracking_source_code(prefix: str, value: str) -> str:
    normalized_value = _clean_text(value)
    slug = slugify(normalized_value)[:32]
    if not slug:
        slug = hashlib.md5(normalized_value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{slug}"[:64]


def _site_action_label(event_type: str, payload: dict | None = None) -> str:
    payload = payload if isinstance(payload, dict) else {}
    normalized_event_type = _clean_text(event_type)
    if normalized_event_type == "page_view":
        return "Просмотр страницы"
    if normalized_event_type == "chat_opened":
        return "Открытие чата"
    if normalized_event_type == "first_message_sent":
        return "Первое сообщение"
    if normalized_event_type == "phone_clicked":
        return "Клик по телефону"
    if normalized_event_type == "messenger_clicked":
        return "Клик по мессенджеру"
    if normalized_event_type == "form_submitted":
        form_type = _clean_text(payload.get("form_type"))
        return f"Клик по форме {form_type}" if form_type else "Отправка формы"
    return normalized_event_type or "Событие сайта"


def _site_action_code(event_type: str, payload: dict | None = None) -> str:
    payload = payload if isinstance(payload, dict) else {}
    normalized_event_type = _clean_text(event_type) or "site_event"
    if normalized_event_type == "form_submitted":
        form_type = _clean_text(payload.get("form_type"))
        if form_type:
            return _tracking_source_code("site-form", form_type)
    return _tracking_source_code("site-action", normalized_event_type)


def build_tracking_actions(session: WebsiteSession | None) -> list[LeadSource]:
    if session is None:
        return []

    actions = []
    seen_codes = set()
    for event in session.events.order_by("created_at", "id"):
        payload = event.payload if isinstance(event.payload, dict) else {}
        code = _site_action_code(event.event_type, payload)
        if code in seen_codes:
            continue
        seen_codes.add(code)
        action, _ = LeadSource.objects.get_or_create(
            code=code,
            defaults={
                "name": _site_action_label(event.event_type, payload)[:128],
                "description": f"Автоматически создано из события сайта {event.event_type}",
                "is_active": True,
            },
        )
        actions.append(action)

    return actions


def _has_yandex_tracking_marker(*, session: WebsiteSession | None, utm_data: dict | None = None) -> bool:
    if session is not None and _clean_text(getattr(session, "yclid", "")):
        return True
    if isinstance(utm_data, dict) and _clean_text(utm_data.get("yclid", "")):
        return True

    markers = []
    if session is not None:
        markers.extend(
            [
                getattr(session, "utm_source", ""),
                getattr(session, "utm_medium", ""),
                getattr(session, "utm_campaign", ""),
                getattr(session, "utm_content", ""),
                getattr(session, "utm_term", ""),
                getattr(session, "yclid", ""),
            ]
        )
    if isinstance(utm_data, dict):
        markers.extend(
            [
                utm_data.get("utm_source", ""),
                utm_data.get("utm_medium", ""),
                utm_data.get("utm_campaign", ""),
                utm_data.get("utm_content", ""),
                utm_data.get("utm_term", ""),
                utm_data.get("yclid", ""),
            ]
        )
    for marker in markers:
        normalized_marker = _clean_text(marker).lower()
        if not normalized_marker:
            continue
        if "yandex" in normalized_marker:
            return True
    return False


def get_primary_tracking_source(
    session: WebsiteSession | None,
    fallback_source: TrafficSource | None = None,
    utm_data: dict | None = None,
) -> TrafficSource | None:
    if _has_yandex_tracking_marker(session=session, utm_data=utm_data):
        source, _ = TrafficSource.objects.get_or_create(
            code=_tracking_source_code("traffic-source", "yandex"),
            defaults={
                "name": "Источник трафика: yandex",
                "description": "Автоматически создано из yandex UTM-метки",
                "is_active": True,
            },
        )
        return source
    return fallback_source


def sync_lead_tracking_data(lead, session: WebsiteSession | None, primary_source: TrafficSource | None = None) -> None:
    if session is None or lead is None:
        return

    effective_primary_source = get_primary_tracking_source(
        session,
        primary_source,
        utm_data=getattr(lead, "utm_data", None),
    )
    update_fields = []
    if getattr(lead, "website_session_id", None) != session.id:
        lead.website_session = session
        update_fields.append("website_session")

    history = build_lead_history(session)
    if getattr(lead, "history", None) != history:
        lead.history = history
        update_fields.append("history")

    if effective_primary_source is not None and getattr(lead, "source_id", None) != effective_primary_source.id:
        lead.source = effective_primary_source
        update_fields.append("source")

    if update_fields:
        update_fields.append("updated_at")
        lead.save(update_fields=update_fields)

    actions_to_add = build_tracking_actions(session)
    if actions_to_add:
        lead.sources.add(*actions_to_add)


def sync_lead_tracking_for_session(session: WebsiteSession | None) -> None:
    if session is None:
        return
    for lead in session.leads.all():
        sync_lead_tracking_data(lead, session, getattr(lead, "source", None))
