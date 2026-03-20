from __future__ import annotations


ACTION_LABELS = {
    "reply": "Ответить",
    "call": "Позвонить",
    "schedule_meeting": "Назначить встречу",
    "create_task": "Создать задачу",
    "check_email": "Проверить email",
    "resend_message": "Отправить повторно",
    "change_channel": "Сменить канал связи",
    "reschedule_meeting": "Перенести встречу",
    "send_proposal": "Отправить КП",
    "prepare_contract": "Подготовить договор",
    "send_materials": "Отправить материалы",
    "revise_proposal": "Скорректировать КП",
    "issue_invoice": "Выставить счёт",
    "launch_project": "Запустить проект",
    "prepare_documents": "Подготовить документы",
}


EVENT_ACTIONS = {
    "email_received": ["reply", "call", "schedule_meeting", "create_task"],
    "telegram_message_received": ["reply", "call", "schedule_meeting", "create_task"],
    "whatsapp_message_received": ["reply", "call", "schedule_meeting", "create_task"],
    "email_bounced": ["check_email", "resend_message", "change_channel"],
    "call_completed": ["schedule_meeting", "send_proposal", "create_task"],
    "call_no_answer": ["call", "create_task"],
    "meeting_cancelled": ["reschedule_meeting", "call", "create_task"],
    "meeting_completed": ["send_proposal", "prepare_contract", "send_materials"],
    "meeting_no_show": ["reschedule_meeting", "call", "create_task"],
    "proposal_revision_requested": ["revise_proposal"],
    "proposal_accepted": ["prepare_contract"],
    "documents_requested": ["prepare_documents"],
    "contract_revision_requested": ["prepare_contract"],
    "contract_agreed": ["issue_invoice"],
    "payment_confirmed": ["launch_project"],
}


def get_available_actions_for_event(event_type: str) -> list[dict]:
    normalized = str(event_type or "").strip()
    action_ids = EVENT_ACTIONS.get(normalized, [])
    actions = []
    for action_id in action_ids:
        label = ACTION_LABELS.get(action_id)
        if not label:
            continue
        actions.append({"id": action_id, "label": label})
    return actions
