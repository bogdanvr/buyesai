from __future__ import annotations

from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from integrations.novofon.selectors import get_novofon_account
from integrations.novofon.services import import_novofon_calls_history


class Command(BaseCommand):
    help = "Импортирует историю звонков Novofon. Подходит для cron."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=None, help="Импортировать последние N дней.")
        parser.add_argument("--today", action="store_true", help="Импортировать звонки за текущий день в часовом поясе Novofon.")
        parser.add_argument("--yesterday", action="store_true", help="Импортировать звонки за предыдущий день в часовом поясе Novofon.")
        parser.add_argument("--hours", type=int, default=None, help="Импортировать последние N часов.")
        parser.add_argument("--date-from", dest="date_from", default="", help="Начало диапазона в ISO-формате.")
        parser.add_argument("--date-till", dest="date_till", default="", help="Конец диапазона в ISO-формате.")
        parser.add_argument("--limit", type=int, default=1000, help="Лимит Novofon API на страницу.")
        parser.add_argument("--max-records", dest="max_records", type=int, default=20000, help="Максимум записей за запуск.")
        parser.add_argument("--include-ongoing-calls", action="store_true", help="Включить незавершенные звонки.")

    def _novofon_timezone(self):
        account = get_novofon_account(create=True)
        timezone_name = str(((account.settings_json or {}).get("novofon_timezone") if account else "") or "").strip() or "UTC"
        try:
            return ZoneInfo(timezone_name)
        except Exception as error:
            raise CommandError(f"Некорректный novofon_timezone: {timezone_name}") from error

    def _parse_iso_datetime(self, value: str):
        raw = str(value or "").strip()
        if not raw:
            return None
        parsed = datetime.fromisoformat(raw)
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def _resolve_range(self, options):
        explicit_date_from = self._parse_iso_datetime(options["date_from"])
        explicit_date_till = self._parse_iso_datetime(options["date_till"])
        if bool(explicit_date_from) != bool(explicit_date_till):
            raise CommandError("Нужно указать обе даты: --date-from и --date-till.")

        flags = [bool(options["today"]), bool(options["yesterday"]), explicit_date_from is not None, options["hours"] is not None, options["days"] is not None]
        if sum(flags) > 1:
            raise CommandError("Используй только один режим диапазона: --today, --yesterday, --hours, --days или явные даты.")

        if explicit_date_from and explicit_date_till:
            return explicit_date_from, explicit_date_till

        novofon_tz = self._novofon_timezone()
        now_local = timezone.now().astimezone(novofon_tz)
        if options["today"]:
            start_local = datetime.combine(now_local.date(), time.min, tzinfo=novofon_tz)
            end_local = now_local
            return start_local, end_local
        if options["yesterday"]:
            yesterday = now_local.date() - timedelta(days=1)
            start_local = datetime.combine(yesterday, time.min, tzinfo=novofon_tz)
            end_local = datetime.combine(yesterday, time.max, tzinfo=novofon_tz)
            return start_local, end_local
        if options["hours"] is not None:
            hours = max(1, int(options["hours"]))
            return now_local - timedelta(hours=hours), now_local
        days = max(1, int(options["days"] or 1))
        return now_local - timedelta(days=days), now_local

    def handle(self, *args, **options):
        account = get_novofon_account(create=True)
        if account is None or not account.enabled:
            raise CommandError("Интеграция Novofon отключена.")

        date_from, date_till = self._resolve_range(options)
        result = import_novofon_calls_history(
            account=account,
            date_from=date_from,
            date_till=date_till,
            limit=options["limit"],
            max_records=options["max_records"],
            include_ongoing_calls=bool(options["include_ongoing_calls"]),
        )
        self.stdout.write(self.style.SUCCESS(str(result)))
