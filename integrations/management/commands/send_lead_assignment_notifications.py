import logging
import math
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import Lead
from integrations.models import UserIntegrationProfile
from integrations.services.email import send_lead_assignment_escalation_email
from integrations.services.telegram import (
    build_lead_assignment_message,
    build_lead_assignment_reply_markup,
    send_telegram_chat_message,
)


logger = logging.getLogger(__name__)
User = get_user_model()


def get_lead_recipients():
    return User.objects.filter(is_active=True, is_staff=True).order_by("id")


class Command(BaseCommand):
    help = "Отправляет уведомления о новых лидах без ответственного: сначала в Telegram, затем на email."

    def _process_email_escalations(self, now):
        escalation_minutes = int(getattr(settings, "LEAD_NOTIFICATION_ESCALATION_MINUTES", 10) or 10)
        escalation_threshold = now - timedelta(minutes=escalation_minutes)
        leads = (
            Lead.objects.filter(
                assigned_to__isnull=True,
                assignment_notification_sent_at__isnull=False,
                assignment_notification_sent_at__lte=escalation_threshold,
                assignment_notification_accepted_at__isnull=True,
                assignment_notification_email_escalated_at__isnull=True,
            )
            .order_by("assignment_notification_sent_at", "id")
        )

        escalated_count = 0
        recipients = list(get_lead_recipients())
        for lead in leads:
            minutes_since_send = max(
                escalation_minutes,
                math.ceil((now - lead.assignment_notification_sent_at).total_seconds() / 60),
            )
            sent_any = False
            for user in recipients:
                profile = UserIntegrationProfile.objects.filter(user=user).only("email").first()
                email = str(getattr(profile, "email", "") or "").strip()
                if not email:
                    continue
                try:
                    sent = send_lead_assignment_escalation_email(
                        email=email,
                        lead=lead,
                        user=user,
                        minutes_since_send=minutes_since_send,
                    )
                except Exception:
                    logger.exception("Failed to send lead escalation email. lead_id=%s user_id=%s", lead.pk, user.pk)
                    continue
                if sent:
                    sent_any = True
            if sent_any:
                Lead.objects.filter(pk=lead.pk).update(assignment_notification_email_escalated_at=now)
                escalated_count += 1
        return escalated_count

    def handle(self, *args, **options):
        now = timezone.now()
        leads = (
            Lead.objects.filter(
                assigned_to__isnull=True,
                assignment_notification_sent_at__isnull=True,
            )
            .order_by("created_at", "id")
        )

        sent_count = 0
        recipients = list(get_lead_recipients())
        for lead in leads:
            lead.ensure_assignment_notification_token()
            message = build_lead_assignment_message(lead=lead)
            reply_markup = build_lead_assignment_reply_markup(lead=lead)
            reminder_sent = False

            for user in recipients:
                profile = UserIntegrationProfile.objects.filter(user=user).only("telegram_chat_id").first()
                chat_id = str(getattr(profile, "telegram_chat_id", "") or "").strip()
                if not chat_id:
                    continue
                try:
                    result = send_telegram_chat_message(chat_id=chat_id, text=message, reply_markup=reply_markup)
                except Exception:
                    logger.exception("Failed to send lead notification. lead_id=%s user_id=%s", lead.pk, user.pk)
                    continue
                if result.get("ok"):
                    reminder_sent = True

            if reminder_sent:
                Lead.objects.filter(pk=lead.pk).update(
                    assignment_notification_sent_at=now,
                    assignment_notification_token=lead.assignment_notification_token,
                )
                sent_count += 1

        escalated_count = self._process_email_escalations(now)
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent lead notifications: {sent_count}; escalated emails: {escalated_count}"
            )
        )
