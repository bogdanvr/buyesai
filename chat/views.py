from django.shortcuts import render

import time
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def chat_token(request):
    # если нужно — проверяй аутентификацию/лимиты/капчу
    user_id = request.user.id if request.user.is_authenticated else None

    now = int(time.time())
    payload = {
        "sub": str(user_id) if user_id else "anon",
        "iat": now,
        "exp": now + int(settings.CHAT_WS_JWT_TTL_SECONDS),
        "origin": request.get_host(),  # опционально
    }

    token = jwt.encode(payload, settings.CHAT_WS_JWT_SECRET, algorithm="HS256")
    return JsonResponse({"token": token, "ws_url": settings.CHAT_WS_URL})
