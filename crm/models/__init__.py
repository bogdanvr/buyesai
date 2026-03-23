from crm.models.activity import (
    Activity,
    TaskCategory,
    TaskType,
    UserRole,
    UserRoleAssignment,
)
from crm.models.automation import (
    AutomationDraft,
    AutomationMessageDraft,
    AutomationOutboundMessage,
    AutomationQueueItem,
    AutomationRule,
    NextStepTemplate,
    OutcomeCatalog,
)
from crm.models.client import Client, ClientDocument, CommunicationChannel
from crm.models.contact import Contact, ContactRole, ContactStatus
from crm.models.deal import Deal, DealDocument
from crm.models.lead import Lead, LeadDocument
from crm.models.source import LeadSource
from crm.models.status import DealStage, LeadStatus
from crm.models.touch import Touch, TouchResult

__all__ = [
    "Activity",
    "TaskCategory",
    "TaskType",
    "UserRole",
    "UserRoleAssignment",
    "AutomationRule",
    "AutomationDraft",
    "AutomationMessageDraft",
    "AutomationOutboundMessage",
    "AutomationQueueItem",
    "NextStepTemplate",
    "Client",
    "ClientDocument",
    "CommunicationChannel",
    "Contact",
    "ContactRole",
    "ContactStatus",
    "Deal",
    "DealDocument",
    "Lead",
    "LeadDocument",
    "LeadSource",
    "LeadStatus",
    "DealStage",
    "OutcomeCatalog",
    "Touch",
    "TouchResult",
]
