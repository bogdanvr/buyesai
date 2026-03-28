"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from crm.admin import crm_admin_site
from integrations.novofon.views import (
    IncomingPhoneCallPopupAPIView,
    NovofonCallAPIView,
    NovofonCheckConnectionAPIView,
    NovofonImportCallsAPIView,
    NovofonSettingsAPIView,
    NovofonSyncEmployeesAPIView,
    NovofonWebhookAPIView,
    PhoneCallDetailAPIView,
    PhoneCallListAPIView,
    TelephonyHealthAPIView,
    TelephonyEventReprocessAPIView,
)
from main.views import (
    mainview,
    dadata_party,
    dadata_party_by_inn,
    RobotsTxtView,
    sendform_view,
    consultant_chat,
    track_website_event_view,
    track_website_session_view,
)
from chat.views import chat_token
from django.contrib.sitemaps.views import sitemap

from .sitemaps import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", crm_admin_site.urls),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("robots.txt", RobotsTxtView.as_view(content_type="text/plain"), name="robots"),
    path("", mainview, name="main"),
    path("send_form", sendform_view, name="send_form"),
    path("api/site-tracking/session/", track_website_session_view, name="track_website_session"),
    path("api/site-tracking/event/", track_website_event_view, name="track_website_event"),
    path("crm/", include("crm.urls")),
    path("api/dadata/party/", dadata_party, name="dadata_party"),
    path("api/dadata/party/by-inn/", dadata_party_by_inn, name="dadata_party_by_inn"),
    path("api/chat/token", chat_token),
    path("api/consultant/chat/", consultant_chat, name="consultant_chat"),
    path("api/integrations/novofon/webhook/", NovofonWebhookAPIView.as_view(), name="integrations-novofon-webhook"),
    path("api/telephony/novofon/settings/", NovofonSettingsAPIView.as_view(), name="telephony-novofon-settings"),
    path("api/telephony/novofon/check-connection/", NovofonCheckConnectionAPIView.as_view(), name="telephony-novofon-check-connection"),
    path("api/telephony/novofon/sync-employees/", NovofonSyncEmployeesAPIView.as_view(), name="telephony-novofon-sync-employees"),
    path("api/telephony/novofon/import-calls/", NovofonImportCallsAPIView.as_view(), name="telephony-novofon-import-calls"),
    path("api/telephony/novofon/call/", NovofonCallAPIView.as_view(), name="telephony-novofon-call"),
    path("api/telephony/calls/", PhoneCallListAPIView.as_view(), name="telephony-calls"),
    path("api/telephony/calls/<int:pk>/", PhoneCallDetailAPIView.as_view(), name="telephony-call-detail"),
    path("api/telephony/incoming-calls/popup/", IncomingPhoneCallPopupAPIView.as_view(), name="telephony-incoming-call-popup"),
    path("api/admin/telephony/health/", TelephonyHealthAPIView.as_view(), name="telephony-health"),
    path("api/admin/telephony/events/<int:pk>/reprocess/", TelephonyEventReprocessAPIView.as_view(), name="telephony-event-reprocess"),
    path("api/v1/", include("api.v1.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
