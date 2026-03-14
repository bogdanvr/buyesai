from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from integrations.models import UserIntegrationProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_integration_profile(sender, instance, created, **kwargs):
    if created:
        UserIntegrationProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_integration_profile(sender, instance, **kwargs):
    UserIntegrationProfile.objects.get_or_create(user=instance)
