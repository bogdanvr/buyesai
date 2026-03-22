from django.core.management.base import BaseCommand, CommandError

from crm_communications.email_inbound import build_imap_poller_from_settings


class Command(BaseCommand):
    help = "Забирает входящие email из IMAP и сохраняет их в CRM Communications."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Максимум писем за один запуск")
        parser.add_argument("--mailbox", type=str, default="", help="IMAP mailbox, по умолчанию из settings")
        parser.add_argument("--search", type=str, default="UNSEEN", help="IMAP search criteria")

    def handle(self, *args, **options):
        poller = build_imap_poller_from_settings(mailbox=options.get("mailbox") or None)
        if not poller.host or not poller.username or not poller.password:
            raise CommandError("IMAP не настроен. Проверьте IMAP_HOST / IMAP_USER / IMAP_PASSWORD.")

        result = poller.poll(
            limit=max(1, int(options.get("limit") or 50)),
            search_criteria=str(options.get("search") or "UNSEEN"),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed={result['processed']} duplicates={result['duplicates']} mailbox={result['mailbox']}"
            )
        )
