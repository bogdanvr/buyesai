from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.views.generic import TemplateView
from dadata import Dadata
from main.services import get_client_ip, send_form_to_telegram
from main.models import FormSubmission
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


@ensure_csrf_cookie
def mainview(request):
    # request_context = RequestContext(request.get_host)
    return render(request, "index.html")


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

    suggestions = []
    for item in result or []:
        data = item.get("data") or {}
        address_value = ""
        address = data.get("address")
        if isinstance(address, dict):
            address_value = address.get("value") or ""
        suggestions.append(
            {
                "value": item.get("value") or "",
                "inn": data.get("inn") or "",
                "kpp": data.get("kpp") or "",
                "ogrn": data.get("ogrn") or "",
                "address": address_value,
            }
        )

    return JsonResponse({"suggestions": suggestions})


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

    form_submission = FormSubmission.objects.create(
        form_type=form_type,
        name=str(clean_payload.get("name") or ""),
        phone=str(clean_payload.get("phone") or ""),
        company=str(clean_payload.get("company") or ""),
        message=str(clean_payload.get("message") or clean_payload.get("comment") or ""),
        payload=clean_payload,
        utm_data=_extract_utm_data(request, clean_payload),
    )

    try:
        telegram_result = send_form_to_telegram(form_type=form_type, payload=clean_payload)
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
