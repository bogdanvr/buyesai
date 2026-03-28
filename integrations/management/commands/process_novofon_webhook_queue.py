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
        parser.add_argument(
            "--failed-backoff-base-sec",
            type=int,
            default=30,
            help="Базовая пауза перед повтором failed-события. Далее используется exponential backoff.",
        )
        parser.add_argument(
            "--failed-backoff-max-sec",
            type=int,
            default=900,
            help="Максимальная пауза перед повтором failed-события.",
        )
        parser.add_argument(
            "--reclaim-stale-processing-after-sec",
            type=int,
            default=300,
            help="Через сколько секунд зависшее processing-событие можно вернуть в обработку. 0 отключает возврат.",
        )

    def handle(self, *args, **options):
        max_retries = options["max_retries"]
        reclaim_after = options["reclaim_stale_processing_after_sec"]
        result = process_novofon_webhook_queue(
            limit=options["limit"],
            retry_failed=bool(options["retry_failed"]),
            max_retries=None if int(max_retries or 0) <= 0 else int(max_retries),
            failed_backoff_base_seconds=int(options["failed_backoff_base_sec"] or 30),
            failed_backoff_max_seconds=int(options["failed_backoff_max_sec"] or 900),
            reclaim_stale_processing_after_seconds=None if int(reclaim_after or 0) <= 0 else int(reclaim_after),
        )
        self.stdout.write(self.style.SUCCESS(str(result)))
