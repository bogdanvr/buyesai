from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.views.generic import TemplateView
from django.utils.text import slugify
from dadata import Dadata
from main.services import get_client_ip, send_form_to_telegram
from main.models import FormSubmission
from main.tracking import (
    extract_tracking_session_id,
    get_or_create_website_session,
    normalize_session_id,
    record_website_event,
)
from crm.models import LeadSource
from crm.services.lead_services import create_lead_from_payload
import ipaddress
import json
import logging
import requests
from urllib.parse import parse_qs, urlparse
from requests import RequestException

logger = logging.getLogger(__name__)
UTM_KEYS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "utm_id",
    "utm_source_platform",
    "utm_creative_format",
    "utm_marketing_tactic",
)


def _normalize_phone_digits(value) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits


def _extract_party_suggestion(item: dict) -> dict:
    data = item.get("data") or {}
    name_data = data.get("name") or {}

    short_with_opf = name_data.get("short_with_opf") if isinstance(name_data, dict) else ""
    value = item.get("value") or short_with_opf or ""
    legal_name = ""
    if isinstance(name_data, dict):
        legal_name = name_data.get("full_with_opf") or name_data.get("full") or ""

    address_value = ""
    address = data.get("address")
    if isinstance(address, dict):
        address_value = address.get("value") or ""

    okved = str(data.get("okved") or "").strip()
    industry = str(data.get("activity") or data.get("okved_name") or data.get("industry") or "").strip()

    okveds = data.get("okveds")
    if isinstance(okveds, list) and okveds:
        main_item = None
        for candidate in okveds:
            if isinstance(candidate, dict) and candidate.get("main"):
                main_item = candidate
                break
        if main_item is None:
            main_item = okveds[0] if isinstance(okveds[0], dict) else None
        if isinstance(main_item, dict):
            if not okved:
                okved = str(main_item.get("code") or main_item.get("okved") or "").strip()
            if not industry:
                industry = str(main_item.get("name") or main_item.get("title") or "").strip()

    if not industry and okved:
        industry = f"ОКВЭД {okved}"

    return {
        "value": str(value or "").strip(),
        "name": str(value or "").strip(),
        "legal_name": str(legal_name or "").strip(),
        "inn": str(data.get("inn") or "").strip(),
        "kpp": str(data.get("kpp") or "").strip(),
        "ogrn": str(data.get("ogrn") or "").strip(),
        "address": str(address_value or "").strip(),
        "industry": industry,
        "okved": okved,
    }


def _extract_party_profile(item: dict) -> dict:
    data = item.get("data") or {}
    name_data = data.get("name") or {}
    management = data.get("management") or {}
    address_data = data.get("address") or {}
    phones = data.get("phones") or []
    emails = data.get("emails") or []
    raw_okveds = data.get("okveds") or []

    okveds = []
    if isinstance(raw_okveds, list):
        for entry in raw_okveds:
            if not isinstance(entry, dict):
                continue
            code = str(entry.get("code") or entry.get("okved") or "").strip()
            name = str(entry.get("name") or entry.get("title") or "").strip()
            if not code and not name:
                continue
            okveds.append(
                {
                    "code": code,
                    "name": name,
                    "main": bool(entry.get("main")),
                }
            )

    main_okved = str(data.get("okved") or "").strip()
    industry = str(data.get("okved_name") or data.get("activity") or data.get("industry") or "").strip()
    primary_okved = next((entry for entry in okveds if entry.get("main")), okveds[0] if okveds else None)
    if not main_okved and primary_okved:
        main_okved = primary_okved.get("code", "")
    if not industry and primary_okved:
        industry = primary_okved.get("name", "")
    if not industry and main_okved:
        industry = f"ОКВЭД {main_okved}"

    phone = ""
    if isinstance(phones, list):
        for phone_item in phones:
            if not isinstance(phone_item, dict):
                continue
            value = phone_item.get("value") or phone_item.get("unrestricted_value")
            if value:
                phone = str(value).strip()
                break

    email = ""
    if isinstance(emails, list):
        for email_item in emails:
            if not isinstance(email_item, dict):
                continue
            value = email_item.get("value") or email_item.get("unrestricted_value")
            if value:
                email = str(value).strip()
                break

    legal_name = ""
    short_name = ""
    if isinstance(name_data, dict):
        legal_name = str(name_data.get("full_with_opf") or name_data.get("full") or "").strip()
        short_name = str(name_data.get("short_with_opf") or name_data.get("short") or "").strip()

    address = ""
    if isinstance(address_data, dict):
        address = str(address_data.get("value") or "").strip()

    director_name = str(management.get("name") or "").strip() if isinstance(management, dict) else ""
    director_position = str(management.get("post") or "").strip() if isinstance(management, dict) else ""

    return {
        "name": short_name or str(item.get("value") or "").strip(),
        "legal_name": legal_name,
        "inn": str(data.get("inn") or "").strip(),
        "kpp": str(data.get("kpp") or "").strip(),
        "ogrn": str(data.get("ogrn") or "").strip(),
        "address": address,
        "okved": main_okved,
        "industry": industry,
        "okveds": okveds,
        "director": {
            "name": director_name,
            "position": director_position,
            "phone": phone,
            "email": email,
        },
    }


def _find_party_profile_by_inn(inn: str, token: str) -> dict | None:
    normalized_inn = str(inn or "").strip()
    if not normalized_inn or not token:
        return None

    try:
        dadata = Dadata(token)
        response = dadata.find_by_id("party", normalized_inn)
    except Exception:
        logger.exception("DaData find_by_id failed for inn=%s", normalized_inn)
        return None

    suggestions = []
    if isinstance(response, dict):
        suggestions = response.get("suggestions") or []
    elif isinstance(response, list):
        suggestions = response

    if not suggestions:
        return None

    first = suggestions[0] if isinstance(suggestions[0], dict) else None
    if not first:
        return None
    return _extract_party_profile(first)


def _get_or_create_form_lead_source(form_type: str) -> LeadSource:
    normalized_form_type = str(form_type or "").strip() or "unknown"
    code_suffix = slugify(normalized_form_type.replace("_", "-")) or "unknown"
    code = f"site-{code_suffix}"[:64]
    source, _ = LeadSource.objects.get_or_create(
        code=code,
        defaults={
            "name": f"Форма сайта: {normalized_form_type}"[:128],
            "description": "Автоматически создано из отправки формы сайта",
            "is_active": True,
        },
    )
    return source


def _extract_utm_from_url(url):
    if not isinstance(url, str):
        return {}
    source = url.strip()
    if not source:
        return {}
    try:
        query = urlparse(source).query if "?" in source or "://" in source else source
        parsed = parse_qs(query, keep_blank_values=True)
    except Exception:
        return {}

    utm_data = {}
    for key in UTM_KEYS:
        values = parsed.get(key) or []
        if not values:
            continue
        value = str(values[-1]).strip()
        if value:
            utm_data[key] = value
    return utm_data


def _extract_utm_data(request, payload):
    result = {}

    payload_utm = payload.get("utm_data")
    if isinstance(payload_utm, dict):
        for key, value in payload_utm.items():
            key_text = str(key).strip()
            if key_text.startswith("utm_") and value not in (None, ""):
                result[key_text] = str(value).strip()

    page_url = payload.get("page_url")
    if isinstance(page_url, str):
        result.update(_extract_utm_from_url(page_url))

    referer = request.META.get("HTTP_REFERER", "")
    if referer:
        result.update(_extract_utm_from_url(referer))

    return result


def _build_tracking_session_payload(request, payload):
    payload = payload if isinstance(payload, dict) else {}
    utm_data = _extract_utm_data(request, payload)
    tracking_payload = {
        "utm_source": str(utm_data.get("utm_source") or payload.get("utm_source") or "").strip(),
        "utm_medium": str(utm_data.get("utm_medium") or payload.get("utm_medium") or "").strip(),
        "utm_campaign": str(utm_data.get("utm_campaign") or payload.get("utm_campaign") or "").strip(),
        "utm_content": str(utm_data.get("utm_content") or payload.get("utm_content") or "").strip(),
        "utm_term": str(utm_data.get("utm_term") or payload.get("utm_term") or "").strip(),
        "yclid": str(payload.get("yclid") or "").strip(),
        "referer": str(payload.get("referer") or request.META.get("HTTP_REFERER") or "").strip(),
        "landing_url": str(payload.get("landing_url") or payload.get("page_url") or "").strip(),
        "client_id": str(payload.get("client_id") or "").strip(),
    }
    return tracking_payload


def _get_tracking_session(request, payload):
    session_id = extract_tracking_session_id(payload)
    if not session_id:
        return None
    return get_or_create_website_session(
        session_id=session_id,
        payload=_build_tracking_session_payload(request, payload),
    )


@ensure_csrf_cookie
def mainview(request):
    # request_context = RequestContext(request.get_host)
    return render(request, "index.html")


@require_POST
def track_website_session_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    session_id = normalize_session_id(payload.get("session_id"))
    if not session_id:
        return JsonResponse({"error": "session_id_required"}, status=400)

    session = get_or_create_website_session(
        session_id=session_id,
        payload=_build_tracking_session_payload(request, payload),
    )
    record_website_event(
        session=session,
        event_type="page_view",
        page_url=str(payload.get("page_url") or payload.get("landing_url") or "").strip(),
        payload={"referrer": str(payload.get("referer") or request.META.get("HTTP_REFERER") or "").strip()},
    )
    return JsonResponse({"ok": True, "session_id": session.session_id})


@require_POST
def track_website_event_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    session_id = normalize_session_id(payload.get("session_id"))
    event_type = str(payload.get("event_type") or "").strip()
    if not session_id:
        return JsonResponse({"error": "session_id_required"}, status=400)
    if not event_type:
        return JsonResponse({"error": "event_type_required"}, status=400)

    session = get_or_create_website_session(
        session_id=session_id,
        payload=_build_tracking_session_payload(request, payload),
    )
    event = record_website_event(
        session=session,
        event_type=event_type,
        page_url=str(payload.get("page_url") or "").strip(),
        payload={
            "message": str(payload.get("message") or "").strip(),
            "href": str(payload.get("href") or "").strip(),
            "label": str(payload.get("label") or "").strip(),
            "form_type": str(payload.get("form_type") or "").strip(),
        },
    )
    if event is None:
        return JsonResponse({"error": "unsupported_event_type"}, status=400)
    return JsonResponse({"ok": True, "session_id": session.session_id, "event_id": event.id})


class RobotsTxtView(TemplateView):
    template_name = "robots.txt"


@require_GET
def dadata_party(request):
    ip = get_client_ip(request)
    query = (request.GET.get("q") or "").strip()
    if len(query) < 2:
        return JsonResponse({"suggestions": []})

    token = getattr(settings, "DADATA_KEY", "")
    if not token:
        return JsonResponse({"suggestions": []}, status=503)

    try:
        dadata = Dadata(token)
        locations_boost = None
        if ip:
            try:
                ip_obj = ipaddress.ip_address(ip)
                if not (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_reserved
                    or ip_obj.is_unspecified
                ):
                    ip_location = dadata.iplocate(ip)
                    location_data = {}
                    if isinstance(ip_location, dict):
                        if isinstance(ip_location.get("data"), dict):
                            location_data = ip_location.get("data") or {}
                        elif isinstance(ip_location.get("location"), dict):
                            location_data = ip_location.get("location") or {}
                        else:
                            location_data = ip_location
                    kladr_id = (
                        location_data.get("city_kladr_id")
                        or location_data.get("settlement_kladr_id")
                        or location_data.get("region_kladr_id")
                        or location_data.get("kladr_id")
                    )
                    if kladr_id:
                        locations_boost = [{"kladr_id": kladr_id}]
            except ValueError:
                locations_boost = None
        if locations_boost:
            result = dadata.suggest("party", query, locations_boost=locations_boost)
            print("r", result)
        else:
            result = dadata.suggest("party", query)
            print("r", result)
    except Exception:
        return JsonResponse({"suggestions": []}, status=502)

    suggestions = [_extract_party_suggestion(item) for item in (result or [])]

    return JsonResponse({"suggestions": suggestions})


@require_GET
def dadata_party_by_inn(request):
    inn = str(request.GET.get("inn") or "").strip()
    if len(inn) < 10:
        return JsonResponse({"error": "inn_required"}, status=400)

    token = getattr(settings, "DADATA_KEY", "")
    if not token:
        return JsonResponse({"error": "dadata_not_configured"}, status=503)

    profile = _find_party_profile_by_inn(inn=inn, token=token)
    if not profile:
        return JsonResponse({"profile": None}, status=404)
    return JsonResponse({"profile": profile})


@require_POST
def sendform_view(request):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    form_type = str(body.get("form_type") or "").strip()
    payload = body.get("payload") or {}
    if not form_type:
        return JsonResponse({"error": "form_type_required"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "payload_must_be_object"}, status=400)

    clean_payload = {}
    for key, value in payload.items():
        if value is None:
            continue
        clean_payload[str(key)] = str(value).strip() if isinstance(value, str) else value

    phone_digits = _normalize_phone_digits(clean_payload.get("phone"))
    if len(phone_digits) != 11 or not phone_digits.startswith("7"):
        return JsonResponse({"error": "phone_required"}, status=400)

    tracking_session = None
    try:
        tracking_session = _get_tracking_session(request, clean_payload)
        if tracking_session is not None:
            clean_payload["session_id"] = tracking_session.session_id
            record_website_event(
                session=tracking_session,
                event_type="form_submitted",
                page_url=str(clean_payload.get("page_url") or "").strip(),
                payload={"form_type": form_type},
            )
    except Exception:
        logger.exception("Tracking failed for send_form form_type=%s", form_type)
        tracking_session = None

    form_submission = FormSubmission.objects.create(
        form_type=form_type,
        name=str(clean_payload.get("name") or ""),
        phone=str(clean_payload.get("phone") or ""),
        company=str(clean_payload.get("company") or ""),
        message=str(clean_payload.get("message") or clean_payload.get("comment") or ""),
        payload=clean_payload,
        utm_data=_extract_utm_data(request, clean_payload),
    )

    crm_lead_id = None
    try:
        lead_payload = dict(clean_payload)
        if "utm_data" not in lead_payload:
            lead_payload["utm_data"] = form_submission.utm_data
        lead_payload["form_submission_id"] = form_submission.id

        company_data = lead_payload.get("company_data")
        merged_company_data = dict(company_data) if isinstance(company_data, dict) else {}
        company_inn = (
            str(merged_company_data.get("inn") or lead_payload.get("company_inn") or "").strip()
        )
        if company_inn:
            dadata_profile = _find_party_profile_by_inn(
                inn=company_inn,
                token=getattr(settings, "DADATA_KEY", ""),
            )
            if dadata_profile:
                merged_company_data.update(dadata_profile)

        if merged_company_data:
            lead_payload["company_data"] = merged_company_data
            lead_payload["company"] = (
                str(merged_company_data.get("name") or lead_payload.get("company") or "").strip()
            )
            lead_payload["company_name"] = str(merged_company_data.get("name") or "").strip()
            lead_payload["company_legal_name"] = str(merged_company_data.get("legal_name") or "").strip()
            lead_payload["company_inn"] = str(merged_company_data.get("inn") or "").strip()
            lead_payload["company_kpp"] = str(merged_company_data.get("kpp") or "").strip()
            lead_payload["company_ogrn"] = str(merged_company_data.get("ogrn") or "").strip()
            lead_payload["company_address"] = str(merged_company_data.get("address") or "").strip()
            lead_payload["company_industry"] = str(merged_company_data.get("industry") or "").strip()
            lead_payload["company_okved"] = str(merged_company_data.get("okved") or "").strip()
            director = merged_company_data.get("director") if isinstance(merged_company_data.get("director"), dict) else {}
            lead_payload["company_director_name"] = str(director.get("name") or "").strip()
            lead_payload["company_director_position"] = str(director.get("position") or "").strip()
            lead_payload["company_director_phone"] = str(director.get("phone") or "").strip()
            lead_payload["company_director_email"] = str(director.get("email") or "").strip()

            persisted_payload = dict(lead_payload)
            persisted_payload.pop("form_submission_id", None)
            form_submission.payload = persisted_payload
            form_submission.company = str(lead_payload.get("company") or form_submission.company or "").strip()
            form_submission.save(update_fields=["payload", "company"])

        source = _get_or_create_form_lead_source(form_type)
        crm_lead = create_lead_from_payload(
            form_type=form_type,
            payload=lead_payload,
            source=source,
            website_session=tracking_session,
        )
        crm_lead_id = crm_lead.id
    except Exception:
        logger.exception(
            "Failed to auto-create crm lead for form_submission_id=%s",
            form_submission.id,
        )

    try:
        telegram_payload = dict(lead_payload)
        telegram_payload.pop("form_submission_id", None)
        telegram_result = send_form_to_telegram(form_type=form_type, payload=telegram_payload)
    except Exception as exc:
        logger.exception("Unexpected telegram send error for submission_id=%s", form_submission.id)
        telegram_result = {"sent": 0, "total": 0, "errors": [f"unexpected_error:{type(exc).__name__}:{exc}"]}

    telegram_ok = telegram_result.get("sent", 0) > 0
    telegram_errors = telegram_result.get("errors") or []
    form_submission.telegram_sent = telegram_ok
    form_submission.telegram_sent_count = int(telegram_result.get("sent") or 0)
    form_submission.telegram_total_targets = int(telegram_result.get("total") or 0)
    form_submission.telegram_errors = "\n".join(str(item) for item in telegram_errors)
    form_submission.save(
        update_fields=[
            "telegram_sent",
            "telegram_sent_count",
            "telegram_total_targets",
            "telegram_errors",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "id": form_submission.id,
            "crm_lead_id": crm_lead_id,
            "telegram_sent": telegram_ok,
            "telegram_result": telegram_result if settings.DEBUG else None,
        }
    )


@require_POST
def consultant_chat(request):
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return JsonResponse({"error": "openai_key_missing"}, status=503)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "empty_message"}, status=400)

    history = payload.get("history") or []
    safe_history = []
    if isinstance(history, list):
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            if role not in ("user", "assistant"):
                continue
            content = (item.get("content") or "").strip()
            if content:
                safe_history.append({"role": role, "content": content[:2000]})

    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    prompt = """
        <system prompt>
ALWAYS ANSWER IN RUSSIAN;
ТЫ — ВЫСОКОКОНВЕРСИОННЫЙ AI-КОНСУЛЬТАНТ ПО ВНЕДРЕНИЮ ИИ И АВТОМАТИЗАЦИИ ДЛЯ МАЛОГО И СРЕДНЕГО БИЗНЕСА.
ТВОЯ ЗАДАЧА — НЕ ПРОСТО ОТВЕЧАТЬ, А ПРОДАВАТЬ ЧЕРЕЗ ДИАГНОСТИКУ БИЗНЕС-ПРОЦЕССОВ И ВЫВОДИТЬ ПОЛЬЗОВАТЕЛЯ НА БЕСПЛАТНЫЙ AI-АУДИТ.
ТЫ ПРОДАЁШЬ:
— AI-АССИСТЕНТОВ ДЛЯ ОТДЕЛОВ
— АВТОМАТИЗАЦИЮ ЗАЯВОК, АНАЛИТИКИ И РУТИНЫ
— ВНЕДРЕНИЕ ЗА 30–60 ДНЕЙ
— ПРОЗРАЧНЫЙ РАСЧЁТ ЭФФЕКТА
— БЕЗОПАСНУЮ РАБОТУ С ДАННЫМИ (NDA, ГОСТ/ISO)
— ИЗМЕРИМЫЕ KPI
ТВОЯ СТРАТЕГИЯ — НЕ "ИИ РАДИ ИИ", А РЕШЕНИЕ КОНКРЕТНОЙ БИЗНЕС-ПРОБЛЕМЫ С ФИНАНСОВЫМ ЭФФЕКТОМ.
--------------------------------------------------------
<role>
ТЫ — СТАРШИЙ БИЗНЕС-АНАЛИТИК И AI-АРХИТЕКТОР С 10+ ЛЕТ ОПЫТА.
ПОНИМАЕШЬ ПРОДАЖИ, СНАБЖЕНИЕ, СЕРВИС, МАРКЕТИНГ.
ГОВОРИШЬ НА ЯЗЫКЕ СОБСТВЕННИКОВ И РУКОВОДИТЕЛЕЙ.
ИСПОЛЬЗУЕШЬ ЦИФРЫ И КОНКРЕТИКУ.
</role>
--------------------------------------------------------
<главная цель>
1. БЫСТРО ВЫЯВИТЬ БОЛЬ
2. ПОКАЗАТЬ ПОТЕНЦИАЛ ЭКОНОМИИ
3. ДАТЬ КОНКРЕТНЫЙ СЦЕНАРИЙ
4. ПЕРЕВЕСТИ НА:
   — ПОЛУЧЕНИЕ AI-СТРАТЕГИИ
   — ИЛИ БЕСПЛАТНЫЙ AI-АУДИТ
   — ИЛИ ОБСУЖДЕНИЕ ПИЛОТА
</главная цель>
--------------------------------------------------------
<структура диалога>
ШАГ 1 — УТОЧНИТЬ КОНТЕКСТ
ЗАДАЙ 1–3 КОНКРЕТНЫХ ВОПРОСА:
— какая отрасль?
— какой отдел?
— где больше всего ручной работы?
— сколько сотрудников?
— сколько заявок в месяц?
ШАГ 2 — ПОКАЗАТЬ ЭФФЕКТ
ОПЕРИРУЙ ЦИФРАМИ:
— -20–40% ручной работы
— +10–25% к выручке
— -15–30% лишних остатков
— -35% нагрузки на поддержку
ШАГ 3 — ПРЕДЛОЖИТЬ РЕШЕНИЕ
ПРЕДЛОЖИ 1 КОНКРЕТНЫЙ СЦЕНАРИЙ:
— AI-ассистент продаж
— AI-аналитика закупок
— AI-бот поддержки
— AI-отчёты и аналитика
ШАГ 4 — ПРИЗЫВ К ДЕЙСТВИЮ
ПРЕДЛОЖИ:
«Можем за 3–5 дней разобрать 1–2 ключевых процесса и прислать PDF с расчётом эффекта. Хотите?»
--------------------------------------------------------
<работа с возражениями>
ЕСЛИ "дорого":
ПОКАЖИ ОКУПАЕМОСТЬ 3–9 МЕСЯЦЕВ.
ЕСЛИ "мало данных":
ОБЪЯСНИ, ЧТО МОЖНО СТАРТОВАТЬ С EXCEL/1С/CRM.
ПОДЧЕРКНИ:
— NDA
— НЕ ОБУЧАЕМ ПУБЛИЧНЫЕ МОДЕЛИ
— МОЖЕМ РАЗВЕРНУТЬ В ИХ КОНТУРЕ
ЕСЛИ "ИИ заменит сотрудников":
АКЦЕНТ НА РАЗГРУЗКУ, А НЕ СОКРАЩЕНИЕ.
--------------------------------------------------------
<тон общения>
— ДЕЛОВОЙ
— КОНКРЕТНЫЙ
— БЕЗ ХАЙПА
— БЕЗ СЛОЖНЫХ ТЕХНИЧЕСКИХ ТЕРМИНОВ
— ФОКУС НА БИЗНЕС-ЭФФЕКТЕ
--------------------------------------------------------
<оптимизация под тип задачи>
CLASSIFICATION:
ОПРЕДЕЛИ ТИП ОТДЕЛА И ПОДБЕРИ СЦЕНАРИЙ.
LEAD QUALIFICATION:
ВЫЯВИ РАЗМЕР КОМАНДЫ И ОБЪЁМ ПРОЦЕССОВ.
GENERATION:
СФОРМИРУЙ ПРЕДВАРИТЕЛЬНЫЙ ПЛАН ИЗ 3 ШАГОВ.
CALCULATION:
ОЦЕНИ ПРИМЕРНУЮ ЭКОНОМИЮ ЧАСОВ.
--------------------------------------------------------
<High Quality Few-Shot Examples>
ПРИМЕР 1 (Продажи)
USER:
У нас отдел продаж, много заявок, менеджеры не успевают.
ASSISTANT:
Сколько заявок в месяц и сколько менеджеров в отделе?
(после ответа)
При 1500 заявках и 5 менеджерах вы, вероятно, теряете 20–30% времени на рутину:
— ответы в мессенджерах
— резюме звонков
— фиксация в CRM
AI-ассистент может:
— отвечать 24/7
— делать сводки диалогов
— подсказывать следующий шаг менеджеру
Обычно это:
-30% времени на рутину
+12–20% к конверсии
Можем за 3–5 дней разобрать процесс и прислать расчёт эффекта. Обсудим?
--------------------------------------------------------
ПРИМЕР 2 (Снабжение)
USER:
Склад забит, много мёртвых остатков.
ASSISTANT:
Сколько SKU и есть ли данные по продажам за 6–12 месяцев?
Обычно в таких случаях:
15–30% капитала заморожено в медленных позициях.
Мы внедряем AI-аналитику, которая:
— выявляет мёртвые позиции
— прогнозирует спрос
— рекомендует объём заказа
Пилот занимает 4–5 недель.
Хотите получить предварительный расчёт экономии?
--------------------------------------------------------
ПРИМЕР НЕПРАВИЛЬНОГО ОТВЕТА:
"Мы используем современные нейросети и большие языковые модели, которые анализируют ваши процессы..."
(ОШИБКА: нет фокуса на бизнес-эффекте, слишком технически)
--------------------------------------------------------
</High Quality Few-Shot Examples>
--------------------------------------------------------
<what not to do>
1. НИКОГДА НЕ УХОДИ В ТЕХНИЧЕСКИЕ ПОДРОБНОСТИ МОДЕЛЕЙ.
2. НЕ ГОВОРИ ПРО "ХАЙП", "ТРЕНДЫ", "РЕВОЛЮЦИЮ ИИ".
3. НЕ ДАВАЙ АБСТРАКТНЫЕ ОБЕЩАНИЯ БЕЗ ЦИФР.
4. НЕ ПРЕДЛАГАЙ ВСЁ СРАЗУ — ТОЛЬКО 1 НАИБОЛЕЕ ПОДХОДЯЩИЙ СЦЕНАРИЙ.
5. НЕ БУДЬ СЛИШКОМ ДЛИННЫМ.
6. НЕ ПУГАЙ ЗАМЕНОЙ СОТРУДНИКОВ.
7. НЕ ОБСУЖДАЙ ВНУТРЕННИЕ ТЕХНОЛОГИИ БЕЗ ЗАПРОСА.
8. НЕ ПРОПУСКАЙ ПРИЗЫВ К ДЕЙСТВИЮ.
9. НЕ ЗАДАВАЙ БОЛЕЕ 3 ВОПРОСОВ ПОДРЯД.
10. НЕ ДАВАЙ ОТВЕТЫ БЕЗ ПОНИМАНИЯ КОНТЕКСТА БИЗНЕСА.
</what not to do>
--------------------------------------------------------
<завершение>
В КАЖДОМ ДИАЛОГЕ СТРЕМИСЬ:
— ПОКАЗАТЬ ЭКОНОМИКУ
— УПРОСТИТЬ СЛОЖНОЕ
— ПЕРЕВЕСТИ В АУДИТ
— СФОРМИРОВАТЬ ДОВЕРИЕ
</завершение>
</system prompt>
        """
    messages = [{"role": "developer", "content": prompt}]
    messages.extend(safe_history)
    messages.append({"role": "user", "content": message[:2000]})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    organization = getattr(settings, "OPENAI_ORG", "")
    project = getattr(settings, "OPENAI_PROJECT", "")
    if organization:
        headers["OpenAI-Organization"] = organization
    if project:
        headers["OpenAI-Project"] = project

    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 400,
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30,
        )
    except RequestException as exc:
        return JsonResponse(
            {
                "error": "openai_request_failed",
                "details": str(exc) if settings.DEBUG else "",
            },
            status=502,
        )

    if response.status_code >= 400:
        details = ""
        try:
            error_payload = response.json()
            details = error_payload.get("error") or error_payload
        except ValueError:
            details = response.text[:2000]

        return JsonResponse(
            {
                "error": "openai_error",
                "status": response.status_code,
                "details": details if settings.DEBUG else "",
            },
            status=502,
        )

    try:
        data = response.json()
    except ValueError:
        return JsonResponse(
            {
                "error": "openai_invalid_response",
                "details": response.text[:2000] if settings.DEBUG else "",
            },
            status=502,
        )

    reply = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    reply = reply.strip()
    if not reply:
        return JsonResponse({"error": "empty_reply"}, status=502)

    return JsonResponse({"reply": reply})
