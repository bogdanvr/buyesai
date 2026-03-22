# CRM Communications Runbook

## Назначение

Этот runbook описывает эксплуатацию модуля `crm_communications`:
- входящие webhooks Telegram;
- входящая почта через IMAP;
- исходящая очередь email / telegram;
- ручная обработка ошибок доставки;
- где смотреть логи и как восстанавливать поток.

## Основные сущности

- `Conversation`: диалог, привязанный к компании / контакту / сделке.
- `Message`: отдельное входящее или исходящее сообщение.
- `MessageAttemptLog`: журнал попыток отправки.
- `MessageWebhookEvent`: журнал входящих webhook событий.
- `DeliveryFailureQueue`: очередь ошибок доставки, требующих ручного действия.

## Штатный цикл обработки

### Telegram inbound

- endpoint: `/api/v1/webhooks/telegram/`
- результат:
  - создаётся или находится `Conversation`;
  - создаётся `Message`;
  - создаётся `Touch`;
  - webhook пишется в `MessageWebhookEvent`.

### Email inbound

- command: `python manage.py fetch_imap_inbox`
- результат:
  - IMAP читает новые письма;
  - письма дедуплицируются по `Message-ID`;
  - создаются `Conversation`, `Message`, `Touch`;
  - вложения сохраняются как `MessageAttachment`.

### Outbound queue

- command: `python manage.py process_communications_outbox`
- обрабатывает due-сообщения по:
  - email
  - telegram

Опции:

```bash
python manage.py process_communications_outbox --limit 100
python manage.py process_communications_outbox --email-only
python manage.py process_communications_outbox --telegram-only
```

## Что смотреть в Django admin

### Диалоги

- `Conversation`
- `ConversationRoute`
- `ParticipantBinding`

Использовать, чтобы:
- проверить, к чему привязан диалог;
- увидеть `requires_manual_binding`;
- проверить route/thread/chat mapping.

### Сообщения

- `Message`
- `MessageAttachment`
- `MessageAttemptLog`

Использовать, чтобы:
- найти исходящее или входящее сообщение;
- посмотреть `status`;
- проверить `provider_message_id`, `external_message_id`;
- разобрать историю повторов и ошибок.

### Входящие события

- `MessageWebhookEvent`

Использовать, чтобы:
- проверить, пришёл ли telegram webhook;
- увидеть статус `processed / failed / ignored`;
- разобрать raw payload и текст ошибки.

### Ошибки доставки

- `DeliveryFailureQueue`

Использовать, чтобы:
- увидеть все сообщения в `failed / requires_manual_retry`;
- назначить ответственного;
- отметить `in_progress / resolved / closed`.

## Ручной recovery flow

### Сценарий 1. Не ушло письмо или telegram

1. Найти запись в `DeliveryFailureQueue`.
2. Открыть связанный `Message`.
3. Проверить:
   - `external_recipient_key`;
   - `contact.email` или `contact.telegram`;
   - `last_error_code`, `last_error_message`;
   - `MessageAttemptLog`.
4. Если проблема в получателе:
   - исправить email / telegram у контакта;
   - либо перепривязать диалог;
   - затем вызвать retry через API или UI.
5. После успешной отправки запись в failure queue перейдёт в `resolved`.

### Сценарий 2. Диалог попал не к той сделке

1. Открыть `Conversation`.
2. Проверить `requires_manual_binding`.
3. Проверить `ConversationRoute`.
4. Выполнить ручную привязку:
   - через UI/API;
   - или через админку.
5. Если ошибка уже попала в `DeliveryFailureQueue`, использовать action перепривязки в API, чтобы обновились:
   - `Conversation`
   - `Message`
   - связанный `Touch`

### Сценарий 3. Сообщение не должно больше отправляться

1. Открыть `DeliveryFailureQueue`.
2. Убедиться, что retry не нужен.
3. Указать комментарий решения.
4. Перевести элемент в:
   - `resolved`, если проблема закрыта;
   - `closed`, если кейс сознательно прекращён.

## Полезные API endpoints

- `GET /api/v1/communications/failures/`
- `POST /api/v1/communications/failures/<id>/retry/`
- `POST /api/v1/communications/failures/<id>/bind/`
- `POST /api/v1/communications/failures/<id>/resolve/`
- `POST /api/v1/communications/failures/<id>/close/`
- `POST /api/v1/communications/messages/<id>/retry/`
- `GET /api/v1/communications/messages/<id>/attempts/`
- `POST /api/v1/communications/conversations/<id>/bind/`

## Рекомендуемый scheduler

Минимальный набор:

```bash
*/2 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py fetch_imap_inbox
* * * * * cd /path/to/project && /path/to/venv/bin/python manage.py process_communications_outbox --limit 100
```

Если позже будет переход на Celery, эти команды можно заменить worker/beat задачами без изменения доменной модели.

## Признаки деградации

Требуют проверки:
- растёт `DeliveryFailureQueue`;
- много `Message` в `queued` с просроченным `next_attempt_at`;
- много `MessageWebhookEvent` в `failed`;
- у диалогов массово `requires_manual_binding = true`;
- IMAP перестал забирать письма, но в ящике Beget они есть.

## Быстрый чек-лист диагностики

1. `python manage.py check`
2. `python manage.py fetch_imap_inbox`
3. `python manage.py process_communications_outbox --limit 20`
4. Проверить `DeliveryFailureQueue`
5. Проверить `MessageAttemptLog`
6. Проверить `MessageWebhookEvent`
7. Проверить связанный `Conversation`
