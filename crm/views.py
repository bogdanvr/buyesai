import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404
from django.shortcuts import render


@staff_member_required
def crm_dashboard(request):
    return render(request, "crm.html")


@staff_member_required
def crm_asset_fallback(request, asset_type: str, filename: str):
    allowed_assets = {
        ("js", "crm-app.js"),
        ("css", "crm.css"),
        ("js", "vendor/vue.global.prod.js"),
    }
    asset_key = (str(asset_type or "").strip(), str(filename or "").strip())
    if asset_key not in allowed_assets:
        raise Http404("Asset not found.")

    asset_path = (Path(settings.BASE_DIR) / "assets" / asset_key[0] / asset_key[1]).resolve()
    assets_root = (Path(settings.BASE_DIR) / "assets").resolve()
    if assets_root not in asset_path.parents or not asset_path.exists():
        raise Http404("Asset not found.")

    content_type, _ = mimetypes.guess_type(str(asset_path))
    return FileResponse(asset_path.open("rb"), content_type=content_type or "application/octet-stream")
