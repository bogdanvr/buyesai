from django.db.models import Count, QuerySet, Sum

from crm.models import Deal


def list_deals() -> QuerySet[Deal]:
    return Deal.objects.select_related("client", "lead", "stage", "owner")


def deals_pipeline_summary() -> list[dict]:
    queryset = (
        list_deals()
        .values("stage__name", "stage__code")
        .annotate(total=Count("id"), amount=Sum("amount"))
        .order_by("stage__name")
    )
    return list(queryset)
