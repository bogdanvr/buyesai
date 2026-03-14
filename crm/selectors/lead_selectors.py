from django.db.models import QuerySet

from crm.models import Lead


def list_leads() -> QuerySet[Lead]:
    return Lead.objects.select_related("status", "source", "client", "assigned_to")


def leads_by_status(status_code: str) -> QuerySet[Lead]:
    return list_leads().filter(status__code=status_code)


def get_lead_or_none(lead_id: int) -> Lead | None:
    return list_leads().filter(id=lead_id).first()
