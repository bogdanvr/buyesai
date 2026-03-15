import hashlib

from django.utils import timezone
from django.utils.text import slugify

from crm.models import LeadSource
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

TRACKING_ACTION_LABELS = {
    "page_view": "Просмотр страницы",
    "chat_opened": "Открытие чата",
    "first_message_sent": "Первое сообщение",
    "form_submitted": "Отправка формы",
    "phone_clicked": "Клик по телефону",
    "messenger_clicked": "Клик по мессенджеру",
}


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


def build_tracking_sources(session: WebsiteSession | None) -> list[LeadSource]:
    if session is None:
        return []

    sources = []
    for field_name, code_prefix, label in TRACKING_SOURCE_DEFINITIONS:
        value = _clean_text(getattr(session, field_name, ""))
        if not value:
            continue
        source, _ = LeadSource.objects.get_or_create(
            code=_tracking_source_code(code_prefix, value),
            defaults={
                "name": f"{label}: {value}"[:128],
                "description": f"Автоматически создано из {field_name}",
                "is_active": True,
            },
        )
        sources.append(source)

    seen_events = set()
    for event_type in session.events.order_by("created_at", "id").values_list("event_type", flat=True):
        if event_type in seen_events:
            continue
        seen_events.add(event_type)
        label = TRACKING_ACTION_LABELS.get(event_type)
        if not label:
            continue
        source, _ = LeadSource.objects.get_or_create(
            code=_tracking_source_code("site-action", event_type),
            defaults={
                "name": f"Действие: {label}"[:128],
                "description": "Автоматически создано из действий пользователя на сайте",
                "is_active": True,
            },
        )
        sources.append(source)

    return sources


def get_primary_tracking_source(
    session: WebsiteSession | None,
    fallback_source: LeadSource | None = None,
) -> LeadSource | None:
    if session is not None:
        utm_source = _clean_text(getattr(session, "utm_source", ""))
        if utm_source:
            source, _ = LeadSource.objects.get_or_create(
                code=_tracking_source_code("traffic-source", utm_source),
                defaults={
                    "name": f"Источник трафика: {utm_source}"[:128],
                    "description": "Автоматически создано из utm_source",
                    "is_active": True,
                },
            )
            return source
    return fallback_source


def sync_lead_tracking_data(lead, session: WebsiteSession | None, primary_source: LeadSource | None = None) -> None:
    if session is None or lead is None:
        return

    effective_primary_source = get_primary_tracking_source(session, primary_source)
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

    sources_to_add = build_tracking_sources(session)
    if primary_source is not None:
        sources_to_add.append(primary_source)
    if effective_primary_source is not None:
        sources_to_add.append(effective_primary_source)
    if sources_to_add:
        lead.sources.add(*sources_to_add)


def sync_lead_tracking_for_session(session: WebsiteSession | None) -> None:
    if session is None:
        return
    for lead in session.leads.all():
        sync_lead_tracking_data(lead, session, getattr(lead, "source", None))
