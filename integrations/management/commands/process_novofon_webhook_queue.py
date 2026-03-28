from __future__ import annotations

from django.core.management.base import BaseCommand

from integrations.novofon.services import process_novofon_webhook_queue


class Command(BaseCommand):
    help = "Обрабатывает очередь webhook-событий Novofon. Подходит для cron/worker loop."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25, help="Сколько событий обработать за один запуск.")
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Повторно брать события со статусом failed вместе с queued.",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=5,
            help="Максимум попыток обработки одного события. 0 отключает ограничение.",
        )

    def handle(self, *args, **options):
        max_retries = options["max_retries"]
        result = process_novofon_webhook_queue(
            limit=options["limit"],
            retry_failed=bool(options["retry_failed"]),
            max_retries=None if int(max_retries or 0) <= 0 else int(max_retries),
        )
        self.stdout.write(self.style.SUCCESS(str(result)))
