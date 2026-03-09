from django import template

from about.models import Contact

register = template.Library()


@register.simple_tag
def get_main_contact():
    """Return latest contact configured in admin."""
    return Contact.objects.order_by("-id").first()
