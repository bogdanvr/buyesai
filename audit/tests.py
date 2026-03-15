from django.test import TestCase

from audit.models import AuditLog
from audit.services import log_model_event
from crm.models import Lead, LeadSource


class AuditServicesTests(TestCase):
    def test_log_model_event_serializes_foreign_keys(self):
        source = LeadSource.objects.create(name="Источник трафика: yandex", code="traffic-source-yandex")
        lead = Lead.objects.create(title="Лид", source=source)

        log_model_event(instance=lead, action="lead.updated")

        audit_entry = AuditLog.objects.filter(action="lead.updated").latest("id")
        self.assertEqual(audit_entry.payload["source"], source.id)
