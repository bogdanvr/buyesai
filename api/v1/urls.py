from django.urls import include, path

urlpatterns = [
    path("communications/", include("api.v1.communications.urls")),
    path("leads/", include("api.v1.leads.urls")),
    path("deals/", include("api.v1.deals.urls")),
    path("deal-documents/", include("api.v1.deal_documents.urls")),
    path("client-documents/", include("api.v1.client_documents.urls")),
    path("lead-documents/", include("api.v1.lead_documents.urls")),
    path("automation-drafts/", include("api.v1.automation_drafts.urls")),
    path("automation-message-drafts/", include("api.v1.automation_message_drafts.urls")),
    path("automation-queue/", include("api.v1.automation_queue.urls")),
    path("contacts/", include("api.v1.contacts.urls")),
    path("clients/", include("api.v1.clients.urls")),
    path("activities/", include("api.v1.activities.urls")),
    path("touches/", include("api.v1.touches.urls")),
    path("settlements/", include("api.v1.settlements.urls")),
    path("meta/", include("api.v1.meta.urls")),
    path("webhooks/", include("api.v1.webhooks.urls")),
]
