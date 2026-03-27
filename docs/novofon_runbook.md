# Novofon Runbook

## Где смотреть проблему

### 1. События webhook

Смотреть модель `TelephonyEventLog`:

- `status`
- `error_text`
- `external_call_id`
- `external_event_id`
- `deduplication_key`

Типовые статусы:

- `queued`
- `processed`
- `failed`
- `ignored_duplicate`

### 2. История звонков

Смотреть модель `PhoneCall`:

- `external_call_id`
- `status`
- `direction`
- `phone_from`
- `phone_to`
- `client_phone_normalized`
- `contact_id / company_id / lead_id / deal_id`

### 3. Сопоставление пользователей

Смотреть `TelephonyUserMapping`:

- есть ли запись для CRM user;
- активна ли она;
- заполнены ли `novofon_employee_id` и `novofon_extension`.

## Типовые сценарии

### Webhook пришел, звонок не создался

Проверить:

1. Есть ли запись в `TelephonyEventLog`.
2. Не вернулся ли `403 invalid_secret`.
3. Есть ли `external_call_id` в payload.
4. Что лежит в `error_text`.

Если событие в `failed`, можно повторно обработать:

```http
POST /api/admin/telephony/events/{id}/reprocess/
```

### Исходящий звонок не запускается

Проверить:

1. `TelephonyProviderAccount.enabled = true`
2. заполнены `api_base_url`, `api_key`, `api_secret`
3. у пользователя есть `TelephonyUserMapping`
4. endpoint `/api/telephony/novofon/call/` не вернул `400`

### Дубликаты webhook

Поведение штатное:

- запись в `TelephonyEventLog` создается;
- событие помечается как `ignored_duplicate`;
- дубль `PhoneCall` не создается.

### Звонок не привязался к CRM-сущности

Проверить:

1. какой номер попал в `client_phone_normalized`
2. есть ли у контакта/компании/лида совпадающий номер
3. есть ли открытая сделка у компании
4. включен ли `create_lead_for_unknown_number`

## Кодовые точки диагностики

- `integrations/novofon/webhook_parser.py`
- `integrations/novofon/services.py`
- `integrations/novofon/client.py`
- `integrations/models.py`

## Что доработать после согласования реального API

- финальный format/signature verification webhook;
- точные endpoint paths и auth-схему Novofon API;
- реальную асинхронную очередь вместо DB-backed process/reprocess модели;
- экран настроек Novofon в CRM;
- полноценный блок истории звонков в карточках;
- realtime popup по входящему звонку.
