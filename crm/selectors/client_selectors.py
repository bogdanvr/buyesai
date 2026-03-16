from django.db.models import Count, QuerySet

from crm.models import Client


def list_clients() -> QuerySet[Client]:
    return Client.objects.prefetch_related("contacts").annotate(
        leads_count=Count("leads", distinct=True),
        deals_count=Count("deals", distinct=True),
    ).order_by("name", "id")


def get_client_or_none(client_id: int) -> Client | None:
    return list_clients().filter(id=client_id).first()
