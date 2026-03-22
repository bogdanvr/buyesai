# CRM Communications: Phase 1 Domain Design

## Цель

Зафиксировать доменную модель модуля переписки для первого релиза:
- единое хранение email и Telegram сообщений;
- отдельное хранение полной переписки, CRM-касаний и технических событий;
- поддержка автопривязки и ручной привязки к компании, контакту и сделке;
- готовность к очередям, retry, идемпотентности и ручной обработке ошибок.

## На что опираемся в текущей CRM

В проекте уже есть базовые сущности:
- `Client` — компания;
- `Deal` — сделка;
- `Contact` — контакт компании;
- `Touch` — CRM-касание/сводка события;
- `Activity` — задача/активность;
- `CommunicationChannel` — справочник каналов.

Ключевой принцип:
- `Touch` не используется как основная таблица переписки;
- полная переписка хранится в отдельном communication-слое;
- `Touch` получает только короткую CRM-сводку по сообщению.

## Каналы первого релиза

- `email`
- `telegram`

В модели нужно сразу оставить пространство для новых каналов, но бизнес-логика первого релиза покрывает только эти два.

## Основные сущности

### 1. `Conversation`

Назначение:
- единый диалог в конкретном канале;
- точка входа для списка переписок в карточке компании и сделки;
- агрегат последней активности и текущей маршрутизации.

Хранит:
- канал (`email`, `telegram`);
- текущее состояние диалога;
- связанные `Client`, `Contact`, `Deal` как агрегированные текущие связи;
- данные для threading/route lookup;
- дату последнего входящего и исходящего сообщения;
- дату последней активности;
- признак, что нужна ручная привязка.

Минимальный рекомендуемый набор полей:
- `channel`
- `subject`
- `client`
- `contact`
- `deal`
- `status`
- `requires_manual_binding`
- `last_message_at`
- `last_incoming_at`
- `last_outgoing_at`
- `last_message`
- `last_message_direction`
- `last_message_preview`

### 2. `ConversationRoute`

Назначение:
- хранить устойчивые маршруты привязки диалога к внешнему идентификатору;
- после первой ручной привязки фиксировать дальнейшую маршрутизацию в ту же сделку;
- заменить абстрактную идею `ConversationBinding` конкретной физической моделью маршрута.

Хранит:
- `conversation`
- `channel`
- `route_type`
- `route_key`
- `client`
- `contact`
- `deal`
- `is_primary`
- `resolved_by`
- `resolved_at`
- `resolution_source`

Примеры `route_type`:
- `telegram_chat`
- `email_thread`
- `email_message_id`
- `email_participant`

Примеры `route_key`:
- Telegram `chat_id`
- канонический email-thread key
- нормализованный внешний participant key

### 3. `ParticipantBinding`

Назначение:
- хранить связь между внешним участником канала и CRM-контактом;
- использовать в `ConversationResolverService`.

Хранит:
- `channel`
- `external_participant_key`
- `external_display_name`
- `client`
- `contact`
- `is_primary`
- `last_seen_at`

Примеры `external_participant_key`:
- `telegram:123456789`
- `email:person@example.com`

### 4. `Message`

Назначение:
- основная таблица сообщений;
- единая модель для inbound и outbound;
- хранение transport-статуса, контента и thread metadata.

Хранит:
- `conversation`
- `channel`
- `direction`
- `message_type`
- `status`
- `client`
- `contact`
- `deal`
- `author_user`
- `external_sender_key`
- `external_recipient_key`
- `subject`
- `body_text`
- `body_html`
- `body_preview`
- `provider_message_id`
- `provider_chat_id`
- `provider_thread_key`
- `external_message_id`
- `in_reply_to`
- `references`
- `queued_at`
- `sending_started_at`
- `sent_at`
- `received_at`
- `delivered_at`
- `failed_at`
- `retry_count`
- `last_error_code`
- `last_error_message`
- `requires_manual_retry`

Примечания:
- `external_message_id` для email — это `Message-ID`;
- `provider_message_id` — ID у transport-провайдера;
- `provider_thread_key` — нормализованный thread identifier;
- `body_preview` хранится отдельно, чтобы не собирать его на лету в списках.

### 5. `MessageAttachment`

Назначение:
- хранить вложения сообщений независимо от CRM-документов сделки/компании;
- при необходимости потом связывать сообщение с CRM-документами отдельной логикой.

Хранит:
- `message`
- `file`
- `original_name`
- `mime_type`
- `size_bytes`
- `content_id`
- `is_inline`
- `provider_attachment_id`

### 6. `MessageAttemptLog`

Назначение:
- лог каждой попытки отправки;
- база для retry, диагностики и ручной обработки.

Хранит:
- `message`
- `attempt_number`
- `transport`
- `started_at`
- `finished_at`
- `status`
- `error_class`
- `error_code`
- `error_message`
- `provider_response_payload`
- `scheduled_retry_at`
- `is_final`

Примеры `error_class`:
- `temporary`
- `permanent`
- `validation`
- `manual_required`

### 7. `MessageWebhookEvent`

Назначение:
- журнал сырого inbound event;
- идемпотентность webhook/polling;
- возможность ручной переобработки входящих событий.

Хранит:
- `channel`
- `event_type`
- `external_event_id`
- `external_message_id`
- `payload`
- `processed_at`
- `processing_status`
- `error_message`

Идемпотентность:
- unique по `(channel, external_event_id)` там, где event id существует;
- fallback dedupe по внешнему message id для email/telegram message.

### 8. `DeliveryFailureQueue`

Назначение:
- явный список сообщений, требующих ручной обработки;
- не подменяет `MessageAttemptLog`, а дополняет его как операционную очередь.

Хранит:
- `message`
- `failure_type`
- `opened_at`
- `last_attempt_log`
- `resolution_status`
- `assigned_to`
- `resolved_at`
- `resolution_comment`

## Статусы сообщений

Канонический набор статусов:
- `draft`
- `queued`
- `sending`
- `sent`
- `delivered`
- `received`
- `failed`
- `requires_manual_retry`

### Смысл статусов

- `draft` — сообщение создано, но ещё не поставлено в очередь.
- `queued` — сообщение поставлено в очередь на отправку.
- `sending` — отправка начата worker'ом.
- `sent` — transport принял сообщение.
- `delivered` — есть подтверждение доставки от провайдера.
- `received` — входящее сообщение принято CRM.
- `failed` — постоянная ошибка, retry не нужен.
- `requires_manual_retry` — retry исчерпан или требуется ручное действие.

### Разрешённые переходы

- `draft -> queued`
- `queued -> sending`
- `sending -> sent`
- `sending -> delivered`
- `sending -> failed`
- `sending -> requires_manual_retry`
- `sent -> delivered`
- `sent -> failed`
- `sent -> requires_manual_retry`
- `failed -> queued` только через ручной retry
- `requires_manual_retry -> queued` только через ручной retry
- inbound сообщение создаётся сразу в `received`

## Где хранится что

### Полная переписка

Хранится в:
- `Conversation`
- `Message`
- `MessageAttachment`

### CRM-касание

Хранится в:
- `Touch`

В `Touch` попадает только краткая сводка:
- канал;
- направление;
- краткий preview;
- связанный `Client / Deal / Contact`;
- ссылка на originating `Message` через bridge-логику следующего этапа.

### Технические события

Хранятся в:
- `MessageAttemptLog`
- `MessageWebhookEvent`
- `DeliveryFailureQueue`

## Правила привязки

### Привязка к компании

Порядок:
1. по существующему `ConversationRoute`;
2. по `ParticipantBinding`;
3. по `Contact.email` / `Contact.telegram`;
4. по email домену не привязываем автоматически;
5. если однозначности нет — conversation остаётся без привязки до ручного решения.

### Привязка к контакту

Порядок:
1. по `ParticipantBinding`;
2. по `Contact.email`;
3. по `Contact.telegram`;
4. если найдено несколько контактов — не автопривязываем.

### Привязка к сделке

Порядок:
1. по существующему primary `ConversationRoute`;
2. если у компании одна активная сделка — автопривязка;
3. если у компании несколько активных сделок — `requires_manual_binding = true`;
4. после ручной привязки все следующие сообщения диалога идут в ту же сделку через `ConversationRoute`.

## ER-схема

```text
Client 1---* Contact
Client 1---* Deal

Client 1---* Conversation
Contact 1---* Conversation
Deal   1---* Conversation

Conversation 1---* ConversationRoute
Conversation 1---* Message

Client 1---* ParticipantBinding
Contact 1---* ParticipantBinding

Message 1---* MessageAttachment
Message 1---* MessageAttemptLog
Message 1---0..1 DeliveryFailureQueue

MessageWebhookEvent -> создает/обновляет -> Conversation / Message
Message -> bridge -> Touch
```

## Индексы и ограничения, которые нужно сразу заложить

### Для `Conversation`
- индекс по `channel`
- индекс по `client`
- индекс по `deal`
- индекс по `last_message_at`
- индекс по `requires_manual_binding`

### Для `ConversationRoute`
- unique по `(channel, route_type, route_key)`
- индекс по `deal`
- индекс по `client`
- индекс по `is_primary`

### Для `ParticipantBinding`
- unique по `(channel, external_participant_key)`
- индекс по `client`
- индекс по `contact`

### Для `Message`
- индекс по `conversation`
- индекс по `channel`
- индекс по `direction`
- индекс по `status`
- индекс по `client`
- индекс по `deal`
- индекс по `provider_message_id`
- unique по `(channel, external_message_id)` там, где внешний ID обязателен

### Для `MessageAttemptLog`
- индекс по `message`
- индекс по `attempt_number`
- индекс по `status`
- индекс по `scheduled_retry_at`

### Для `MessageWebhookEvent`
- unique по `(channel, external_event_id)` при наличии event id
- индекс по `external_message_id`
- индекс по `processing_status`

### Для `DeliveryFailureQueue`
- unique по `message`
- индекс по `resolution_status`
- индекс по `assigned_to`

## Что считаем готовым по Phase 1

Phase 1 считается завершённой, когда:
- утверждён список моделей;
- утверждены связи между ними;
- утверждён список статусов сообщения;
- утверждены правила переходов статусов;
- зафиксировано, что `Touch` не хранит полную переписку;
- зафиксировано, что физическая модель маршрутизации называется `ConversationRoute`.

## Следующий шаг

Следующий пункт реализации:
- создать app `crm_communications`;
- перенести эту схему в реальные Django models и миграции.
