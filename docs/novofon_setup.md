# Novofon Setup

## Что реализовано

- хранение настроек провайдера Novofon в CRM;
- синхронизация сотрудников Novofon в таблицу сопоставлений;
- webhook endpoint `POST /api/integrations/novofon/webhook/`;
- queue processor `python manage.py process_novofon_webhook_queue`;
- запуск исходящего звонка через `POST /api/telephony/novofon/call/`;
- ручной импорт исторических звонков через `POST /api/telephony/novofon/import-calls/`;
- журнал событий телефонии;
- модель истории звонков `PhoneCall`;
- API истории звонков:
  - `GET /api/telephony/calls/`
  - `GET /api/telephony/calls/{id}/`
- polling endpoint для popup входящего звонка:
  - `GET /api/telephony/incoming-calls/popup/`
- health endpoint по очереди webhook:
  - `GET /api/admin/telephony/health/`
- reprocess событий:
  - `POST /api/admin/telephony/events/{id}/reprocess/`

## Первичная настройка

1. Применить миграции:

```bash
env/bin/python manage.py migrate
```

2. Открыть admin CRM и создать/проверить аккаунт телефонии `Novofon`.

3. Заполнить поля:

- `enabled`
- `api_key`
- `api_secret`
- `api_base_url`
- `webhook_path`
- `default_owner`
- `create_lead_for_unknown_number`
- `create_task_for_missed_call`
- `link_calls_to_open_deal_only`
- `allowed_virtual_numbers`
- `is_debug_logging_enabled`
- `webhook_shared_secret`

4. Проверить webhook URL.
5. Настроить фоновую обработку webhook-событий.

Рекомендуемый вариант: `systemd service` из `deploy/systemd/buyesai-process-novofon-webhook-queue.service`.

Fallback-вариант через cron:

```bash
* * * * * /path/to/python manage.py process_novofon_webhook_queue --limit 50 --retry-failed
```

Рекомендуемые значения для Novofon:

- `api_key`:
  access token / API key Novofon
- `api_secret`:
  секрет API. Если заполнен, CRM начинает требовать webhook header `Signature` и проверяет его по HMAC-SHA1/Base64
- `api_base_url`:
  `https://dataapi-jsonrpc.novofon.ru/v2.0`
- `settings_json.call_api_base_url`:
  `https://callapi-jsonrpc.novofon.ru/v4.0`

Если в `.env` задан `CRM_PUBLIC_BASE_URL`, CRM соберет полный URL автоматически.
Иначе в API/админке будет показан только path.

## Синхронизация сотрудников

Вызвать:

```http
POST /api/telephony/novofon/sync-employees/
```

После синхронизации в таблице `TelephonyUserMapping` появятся сотрудники Novofon.
Дальше им нужно назначить пользователей CRM.

## Обработка webhook очереди

`POST /api/integrations/novofon/webhook/` теперь только принимает событие и ставит его в очередь.
Фактическая обработка происходит отдельной командой или systemd worker:

```bash
python manage.py process_novofon_webhook_queue --limit 50 --retry-failed
```
Рекомендуемый вариант: отдельный `systemd service` c интервалом `5` секунд.

## Безопасность webhook

Если у аккаунта заполнен `api_secret`, endpoint `/api/integrations/novofon/webhook/` принимает только webhook с корректным header `Signature`.
Дополнительно можно оставить `webhook_shared_secret`: тогда CRM будет требовать и подпись, и shared secret.

Поддерживаемые имена signature header:

- `Signature`
- `X-Signature`
- `X-Novofon-Signature`

Поддерживаемые поля канонического payload для webhook-обработки и проверки подписи:

- `event`
- `pbx_call_id`
- `caller_id`
- `called_did`
- `destination`
- `internal`
- `call_start`
- `notification_time`
- `disposition`

Если webhook приходит в старом адаптационном формате CRM, но у аккаунта уже включен `api_secret`, endpoint вернет `403 unsupported_signature_payload`.

## Импорт исторических звонков

Вызвать:

```http
POST /api/telephony/novofon/import-calls/
Content-Type: application/json
```

Пример payload:

```json
{
  "days": 30,
  "limit": 500,
  "max_records": 5000,
  "include_ongoing_calls": false
}
```

Или с явным диапазоном:

```json
{
  "date_from": "2026-03-01T00:00:00+06:00",
  "date_till": "2026-03-27T23:59:59+06:00",
  "limit": 500,
  "max_records": 5000
}
```

Ограничения:

- Novofon `get.calls_report` позволяет импортировать период не более 90 дней за один запуск;
- импорт идемпотентен: повторный запуск обновляет уже существующие `PhoneCall`, а не создает дубли.

## Настройки API

Получение текущих настроек:

```http
GET /api/telephony/novofon/settings/
```

Обновление:

```http
PUT /api/telephony/novofon/settings/
Content-Type: application/json
```

Пример payload:

```json
{
  "enabled": true,
  "api_key": "novofon-access-token",
  "api_secret": "",
  "api_base_url": "https://dataapi-jsonrpc.novofon.ru/v2.0",
  "webhook_path": "/api/integrations/novofon/webhook/",
  "default_owner": 1,
  "create_lead_for_unknown_number": false,
  "create_task_for_missed_call": true,
  "link_calls_to_open_deal_only": true,
  "allowed_virtual_numbers": ["74950000000"],
  "is_debug_logging_enabled": true,
  "webhook_shared_secret": "shared-secret",
  "settings_json": {
    "call_api_base_url": "https://callapi-jsonrpc.novofon.ru/v4.0"
  },
  "mappings": [
    {
      "novofon_employee_id": "emp-1",
      "crm_user": 1,
      "novofon_extension": "101",
      "novofon_full_name": "Manager One",
      "is_active": true,
      "is_default_owner": false
    }
  ]
}
```

## Что использует CRM сейчас

- `Data API` используется для проверки подключения, получения сотрудников и виртуальных номеров;
- `Call API` используется для запуска исходящего звонка;
- `api_base_url` в CRM означает именно `Data API base URL`;
- `Call API base URL` хранится в `settings_json.call_api_base_url`, если не задан, используется официальный дефолт `https://callapi-jsonrpc.novofon.ru/v4.0`;
- webhook parser все еще остается адаптационным слоем, потому что контракт webhook отдельно от `Data API` / `Call API`.
- popup входящего звонка в CRM работает через polling `GET /api/telephony/incoming-calls/popup/` с интервалом `5` секунд и не требует отдельного websocket stack.

## Ручная проверка

1. Создать аккаунт Novofon и включить интеграцию.
2. Синхронизировать сотрудников.
3. Назначить CRM user в `TelephonyUserMapping`.
4. Отправить тестовый webhook на `POST /api/integrations/novofon/webhook/`.
5. Убедиться, что создан `PhoneCall`.
6. Открыть карточку лида/компании/контакта/сделки и проверить кнопку `CRM` рядом с телефоном.
7. Запустить исходящий звонок из CRM.
