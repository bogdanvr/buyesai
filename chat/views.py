from django.shortcuts import render

import time
import uuid
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def chat_token(request):
    # если нужно — проверяй аутентификацию/лимиты/капчу
    cookie_name = "anon_id"
    response = None

    if request.user.is_authenticated:
        user_value = None
        if hasattr(request.user, "uuid"):
            user_value = getattr(request.user, "uuid")
        if user_value is None:
            user_value = getattr(request.user, "id", None) or getattr(request.user, "pk", None)
        sub = f"user:{user_value}"
    else:
        anon_id = request.COOKIES.get(cookie_name)
        try:
            anon_uuid = uuid.UUID(anon_id) if anon_id else None
        except (ValueError, TypeError):
            anon_uuid = None
        if anon_uuid is None:
            anon_uuid = uuid.uuid4()
        sub = f"anon:{anon_uuid}"

    now = int(time.time())
    payload = {
        "sub": str(sub),
        "iat": now,
        "exp": now + int(settings.CHAT_WS_JWT_TTL_SECONDS),
        "origin": request.get_host(),  # опционально
    }

    token = jwt.encode(payload, settings.CHAT_WS_JWT_SECRET, algorithm="HS256")
    response = JsonResponse({"token": token, "ws_url": settings.CHAT_WS_URL})
    if not request.user.is_authenticated:
        response.set_cookie(
            cookie_name,
            value=str(sub).split("anon:", 1)[-1],
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="Lax",
            secure=not settings.DEBUG,
        )
    return response
