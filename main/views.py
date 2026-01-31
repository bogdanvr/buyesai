from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from dadata import Dadata
from main.services import get_client_ip
import ipaddress


def mainview(request):
    # request_context = RequestContext(request.get_host)
    return render(request, 'index.html')


@require_GET
def dadata_party(request):
    ip = get_client_ip(request)
    print('ip', ip)
    query = (request.GET.get('q') or '').strip()
    if len(query) < 2:
        return JsonResponse({"suggestions": []})

    token = getattr(settings, 'DADATA_KEY', '')
    if not token:
        return JsonResponse({"suggestions": []}, status=503)

    try:
        dadata = Dadata(token)
        locations_boost = None
        if ip:
            try:
                ip_obj = ipaddress.ip_address(ip)
                if not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_unspecified):
                    locations_boost = [{"ip": ip}]
            except ValueError:
                locations_boost = None
        if locations_boost:
            result = dadata.suggest("party", query, locations_boost=locations_boost)
        else:
            result = dadata.suggest("party", query)
    except Exception:
        return JsonResponse({"suggestions": []}, status=502)

    suggestions = []
    for item in result or []:
        data = item.get('data') or {}
        suggestions.append({
            "value": item.get('value') or '',
            "inn": data.get('inn') or '',
            "kpp": data.get('kpp') or '',
            "ogrn": data.get('ogrn') or '',
        })

    return JsonResponse({"suggestions": suggestions})
