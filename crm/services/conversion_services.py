from crm.models import Deal, Lead


def lead_conversion_rate() -> float:
    total = Lead.objects.count()
    if total == 0:
        return 0.0
    converted = Lead.objects.exclude(converted_at__isnull=True).count()
    return round((converted / total) * 100, 2)


def deal_win_rate() -> float:
    total = Deal.objects.count()
    if total == 0:
        return 0.0
    won = Deal.objects.filter(is_won=True).count()
    return round((won / total) * 100, 2)
