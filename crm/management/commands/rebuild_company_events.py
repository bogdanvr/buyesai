import re
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from crm.models import Activity, Client, Deal, Touch
from crm.models.activity import ActivityType, TaskStatus
from crm.signals import (
    ACTIVE_TASK_STATUSES,
    _actor_display_name,
    _format_structured_event_entry,
    _task_status_label,
    _touch_channel_label,
    _touch_direction_label,
    _touch_result_label,
    _touch_title,
)


TIMESTAMP_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}$")


def parse_event_chunks(raw_value: str) -> list[tuple[datetime, str]]:
    raw = str(raw_value or "").strip()
    if not raw:
      return []

    chunks: list[tuple[datetime, str]] = []
    current_tz = timezone.get_current_timezone()
    for chunk in re.split(r"\n\s*\n+", raw):
        normalized = str(chunk or "").strip()
        if not normalized:
            continue
        first_line = normalized.splitlines()[0].strip()
        if TIMESTAMP_RE.match(first_line):
            parsed = datetime.strptime(first_line, "%d.%m.%Y %H:%M")
            happened_at = timezone.make_aware(parsed, current_tz)
        else:
            happened_at = timezone.now()
        chunks.append((happened_at, normalized))
    return chunks


class Command(BaseCommand):
    help = "Пересобирает company.events из сделок, задач и касаний."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, dest="company_id")
        parser.add_argument("--dry-run", action="store_true", dest="dry_run")

    def handle(self, *args, **options):
        company_id = options.get("company_id")
        dry_run = bool(options.get("dry_run"))

        queryset = Client.objects.all().only("id", "name", "events")
        if company_id:
            queryset = queryset.filter(pk=company_id)

        total = 0
        updated = 0

        for company in queryset.iterator():
            total += 1
            events = self.build_company_events(company)
            if str(company.events or "").strip() == events:
                self.stdout.write(f"[skip] {company.id} {company.name}")
                continue
            updated += 1
            if not dry_run:
                Client.objects.filter(pk=company.pk).update(events=events)
            self.stdout.write(f"[{'dry' if dry_run else 'ok'}] {company.id} {company.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: обработано {total}, {'будет обновлено' if dry_run else 'обновлено'} {updated}."
            )
        )

    def build_company_events(self, company: Client) -> str:
        chunks: list[tuple[datetime, str, str]] = []

        deals = (
            Deal.objects.filter(client_id=company.id)
            .only("id", "title", "events", "created_at", "client_id", "is_won", "closed_at", "currency", "amount")
            .order_by("-created_at", "-id")
        )
        for deal in deals:
            parsed_chunks = parse_event_chunks(deal.events)
            if parsed_chunks:
                for happened_at, entry in parsed_chunks:
                    chunks.append((happened_at, entry, f"deal:{deal.id}:{happened_at.timestamp()}"))
                continue
            entry = _format_structured_event_entry(
                result_text=f"Сделка создана: {deal.title}",
                happened_at=deal.created_at,
                deal_id=deal.id,
                event_type="system",
                priority="low",
                extra_lines=["title: Системное событие"],
            )
            chunks.append((deal.created_at or timezone.now(), entry, f"deal-created:{deal.id}"))

        standalone_tasks = (
            Activity.objects.filter(type=ActivityType.TASK, deal__isnull=True)
            .filter(Q(client_id=company.id) | Q(lead__client_id=company.id))
            .select_related("task_type", "created_by", "lead")
            .distinct()
            .order_by("-created_at", "-id")
        )
        for task in standalone_tasks:
            created_entry = _format_structured_event_entry(
                result_text=f"Создана задача: {task.subject}",
                happened_at=task.created_at,
                task_id=task.pk,
                deal_id=None,
                event_type="task",
                priority="medium" if task.status in ACTIVE_TASK_STATUSES else "low",
                extra_lines=[
                    f"title: Задача: {task.subject}",
                    getattr(task.task_type, "name", "") and f"task_type_name: {task.task_type.name}",
                    f"task_status_label: {_task_status_label(task.status)}",
                    task.due_at and f"due_at: {timezone.localtime(task.due_at).isoformat()}",
                    f"owner_name: {_actor_display_name(getattr(task, 'created_by', None))}",
                ],
            )
            chunks.append((task.created_at or timezone.now(), created_entry, f"task-created:{task.id}"))

            result_text = str(task.result or "").strip()
            if task.status == TaskStatus.DONE and result_text:
                completed_at = task.completed_at or task.updated_at or task.created_at or timezone.now()
                done_entry = _format_structured_event_entry(
                    result_text=result_text,
                    happened_at=completed_at,
                    task_id=task.pk,
                    deal_id=None,
                    event_type="task",
                    priority="low",
                    extra_lines=[
                        f"title: Задача: {task.subject}",
                        getattr(task.task_type, "name", "") and f"task_type_name: {task.task_type.name}",
                        f"task_status_label: {_task_status_label(task.status)}",
                        task.due_at and f"due_at: {timezone.localtime(task.due_at).isoformat()}",
                        f"owner_name: {_actor_display_name(getattr(task, 'created_by', None))}",
                        f"task_result: {result_text}",
                    ],
                )
                chunks.append((completed_at, done_entry, f"task-done:{task.id}"))

        standalone_touches = (
            Touch.objects.filter(deal__isnull=True)
            .filter(Q(client_id=company.id) | Q(lead__client_id=company.id))
            .select_related("channel", "result_option", "owner", "lead")
            .distinct()
            .order_by("-happened_at", "-id")
        )
        for touch in standalone_touches:
            result_label = _touch_result_label(touch)
            channel_label = _touch_channel_label(touch)
            direction_label = _touch_direction_label(touch.direction)
            base_text = result_label or str(touch.summary or "").strip() or f"{direction_label} касание"
            entry = _format_structured_event_entry(
                result_text=f"Касание: {base_text}",
                happened_at=touch.happened_at,
                touch_id=touch.pk,
                deal_id=None,
                event_type="touch",
                priority="high",
                extra_lines=[
                    f"title: {_touch_title(touch)}",
                    f"actor_name: {_actor_display_name(touch.owner)}",
                    channel_label and f"channel_name: {channel_label}",
                    f"direction_label: {_touch_direction_label(touch.direction)}",
                    result_label and f"touch_result: {result_label}",
                    touch.summary and f"summary: {touch.summary}",
                    touch.next_step and f"next_step: {touch.next_step}",
                    touch.next_step_at and f"next_step_at: {timezone.localtime(touch.next_step_at).isoformat()}",
                ],
            )
            chunks.append((touch.happened_at or timezone.now(), entry, f"touch:{touch.id}"))

        deduped: list[tuple[datetime, str]] = []
        seen_keys: set[str] = set()
        for happened_at, entry, key in sorted(chunks, key=lambda item: (item[0], item[2]), reverse=True):
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append((happened_at, entry))

        return "\n\n".join(entry for _, entry in deduped)
