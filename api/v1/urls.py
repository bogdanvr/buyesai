from django.urls import include, path

urlpatterns = [
    path("leads/", include("api.v1.leads.urls")),
    path("deals/", include("api.v1.deals.urls")),
    path("deal-documents/", include("api.v1.deal_documents.urls")),
    path("contacts/", include("api.v1.contacts.urls")),
    path("clients/", include("api.v1.clients.urls")),
    path("activities/", include("api.v1.activities.urls")),
    path("touches/", include("api.v1.touches.urls")),
    path("meta/", include("api.v1.meta.urls")),
    path("webhooks/", include("api.v1.webhooks.urls")),
]
