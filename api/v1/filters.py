from django.db.models import Q


def apply_text_search(queryset, search_query: str, fields: list[str]):
    query = (search_query or "").strip()
    if not query:
        return queryset
    condition = Q()
    for field in fields:
        condition |= Q(**{f"{field}__icontains": query})
    return queryset.filter(condition)
