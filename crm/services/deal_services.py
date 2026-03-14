from django.db import transaction
from django.utils import timezone

from crm.models import Deal


@transaction.atomic
def create_deal(*, title: str, client, lead=None, stage=None, amount=0, owner=None) -> Deal:
    return Deal.objects.create(
        title=title,
        client=client,
        lead=lead,
        stage=stage,
        amount=amount,
        owner=owner,
    )


@transaction.atomic
def close_deal(*, deal: Deal, is_won: bool) -> Deal:
    deal.is_won = is_won
    deal.closed_at = timezone.now()
    deal.save(update_fields=["is_won", "closed_at", "updated_at"])
    return deal
