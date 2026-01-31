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
                    ip_location = dadata.iplocate(ip)
                    location_data = {}
                    if isinstance(ip_location, dict):
                        if isinstance(ip_location.get('data'), dict):
                            location_data = ip_location.get('data') or {}
                        elif isinstance(ip_location.get('location'), dict):
                            location_data = ip_location.get('location') or {}
                        else:
                            location_data = ip_location
                    kladr_id = (
                        location_data.get('city_kladr_id')
                        or location_data.get('settlement_kladr_id')
                        or location_data.get('region_kladr_id')
                        or location_data.get('kladr_id')
                    )
                    if kladr_id:
                        locations_boost = [{"kladr_id": kladr_id}]
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
        address_value = ''
        address = data.get('address')
        if isinstance(address, dict):
            address_value = address.get('value') or ''
        suggestions.append({
            "value": item.get('value') or '',
            "inn": data.get('inn') or '',
            "kpp": data.get('kpp') or '',
            "ogrn": data.get('ogrn') or '',
            "address": address_value,
        })

    return JsonResponse({"suggestions": suggestions})
