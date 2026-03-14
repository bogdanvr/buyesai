from django.db.models import Count, Sum

from crm.models import Deal, Lead


def dashboard_totals() -> dict:
    total_leads = Lead.objects.count()
    total_converted = Lead.objects.exclude(converted_at__isnull=True).count()
    conversion_rate = (total_converted / total_leads * 100) if total_leads else 0
    deals_total = Deal.objects.count()
    deals_won = Deal.objects.filter(is_won=True).count()
    won_amount = Deal.objects.filter(is_won=True).aggregate(total=Sum("amount")).get("total") or 0

    return {
        "total_leads": total_leads,
        "converted_leads": total_converted,
        "lead_conversion_rate": round(conversion_rate, 2),
        "total_deals": deals_total,
        "won_deals": deals_won,
        "won_amount": won_amount,
    }
