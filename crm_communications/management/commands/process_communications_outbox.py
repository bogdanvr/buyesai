from django.core.management.base import BaseCommand

from crm_communications.email_outbound import EmailOutboundMessageService
from crm_communications.services import TelegramOutboundMessageService


class Command(BaseCommand):
    help = "Обрабатывает исходящую очередь CRM Communications по email и telegram."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Максимум сообщений на канал за запуск.")
        parser.add_argument("--email-only", action="store_true", help="Обрабатывать только email очередь.")
        parser.add_argument("--telegram-only", action="store_true", help="Обрабатывать только telegram очередь.")

    def handle(self, *args, **options):
        limit = max(int(options.get("limit") or 50), 1)
        email_only = bool(options.get("email_only"))
        telegram_only = bool(options.get("telegram_only"))

        if email_only and telegram_only:
            self.stderr.write("Нельзя одновременно указывать --email-only и --telegram-only.")
            return

        totals = {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "manual_retry": 0,
        }

        def merge(result: dict, *, label: str):
            self.stdout.write(
                f"{label}: processed={result['processed']} sent={result['sent']} failed={result['failed']} manual_retry={result['manual_retry']}"
            )
            for key in totals:
                totals[key] += int(result.get(key) or 0)

        if not telegram_only:
            merge(EmailOutboundMessageService.send_due_messages(limit=limit), label="email")
        if not email_only:
            merge(TelegramOutboundMessageService.send_due_messages(limit=limit), label="telegram")

        self.stdout.write(
            self.style.SUCCESS(
                f"done: processed={totals['processed']} sent={totals['sent']} failed={totals['failed']} manual_retry={totals['manual_retry']}"
            )
        )
