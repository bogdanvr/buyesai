# Systemd Workers

Этот документ описывает перевод фоновых poller/worker задач с cron на `systemd service`.

## Что переводим

- `process_communications_outbox`
- `fetch_imap_inbox`
- `process_novofon_webhook_queue`

## Файлы в репозитории

- unit files: `deploy/systemd/*.service`
- loop scripts: `scripts/systemd/*.sh`

## Рекомендуемые интервалы

- outbox worker: каждые `5` секунд
- IMAP poller: каждые `60` секунд
- Novofon webhook queue: каждые `5` секунд

## Установка

Скопировать unit-файлы:

```bash
sudo cp deploy/systemd/buyesai-process-communications-outbox.service /etc/systemd/system/
sudo cp deploy/systemd/buyesai-fetch-imap-inbox.service /etc/systemd/system/
sudo cp deploy/systemd/buyesai-process-novofon-webhook-queue.service /etc/systemd/system/
```

Сделать скрипты исполняемыми:

```bash
chmod +x scripts/systemd/run_process_communications_outbox.sh
chmod +x scripts/systemd/run_fetch_imap_inbox.sh
chmod +x scripts/systemd/run_process_novofon_webhook_queue.sh
```

Перечитать конфигурацию и включить сервисы:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now buyesai-process-communications-outbox.service
sudo systemctl enable --now buyesai-fetch-imap-inbox.service
sudo systemctl enable --now buyesai-process-novofon-webhook-queue.service
```

## Проверка

```bash
systemctl status buyesai-process-communications-outbox.service
systemctl status buyesai-fetch-imap-inbox.service
systemctl status buyesai-process-novofon-webhook-queue.service
```

Логи:

```bash
journalctl -u buyesai-process-communications-outbox.service -f
journalctl -u buyesai-fetch-imap-inbox.service -f
journalctl -u buyesai-process-novofon-webhook-queue.service -f
```

## Настройка

Если пути или пользователь отличаются, поправить в unit-файлах:

- `User`
- `Group`
- `WorkingDirectory`
- `Environment=PROJECT_DIR=...`
- `Environment=PYTHON_BIN=...`

Также можно менять интервалы и лимиты через `Environment=...`:

- `PROCESS_COMMUNICATIONS_OUTBOX_INTERVAL_SEC`
- `PROCESS_COMMUNICATIONS_OUTBOX_LIMIT`
- `FETCH_IMAP_INBOX_INTERVAL_SEC`
- `FETCH_IMAP_INBOX_LIMIT`
- `FETCH_IMAP_INBOX_SEARCH`
- `FETCH_IMAP_INBOX_MAILBOX`
- `NOVOFON_WEBHOOK_QUEUE_INTERVAL_SEC`
- `NOVOFON_WEBHOOK_QUEUE_LIMIT`
- `NOVOFON_WEBHOOK_QUEUE_MAX_RETRIES`
- `NOVOFON_WEBHOOK_QUEUE_RETRY_FAILED`
