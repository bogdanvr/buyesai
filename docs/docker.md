# Запуск в Docker с PostgreSQL на сервере

Требуются Docker Engine / Docker Desktop и Docker Compose v2.
PostgreSQL работает на сервере вне Docker. Compose не создаёт и не запускает БД.

## Состав

- `setup`: ожидает подключения к PostgreSQL, запускает миграции и `collectstatic`.
- `web`: Django ASGI через Uvicorn, по умолчанию два процесса.
- `nginx`: HTTP на `127.0.0.1:8080`, статика `/assets/` и файлы `/media/`.
- `outbox`, `novofon`: существующие обработчики очередей в отдельных контейнерах.
- `imap`: опциональный сборщик почты, включается профилем `mail`.

Статика и загруженные файлы хранятся в томах `static_data` и `media_data`.
Приложение и обработчики запускаются от пользователя `app`, а не root.
LibreOffice и шрифты для конвертации документов в PDF включены в образ.
WebSocket-сервис чата находится вне этого репозитория: его адрес задаётся
через `CHAT_WS_URL`, а `CHAT_WS_JWT_SECRET` должен совпадать с секретом сервиса.

## Переменные окружения

Для новой установки:

```bash
cp .env.example .env
```

Если `.env` уже существует, перенести в него нужные параметры из примера,
сохранив токены, почтовые пароли и `INTEGRATIONS_SECRET_KEY`. Пример не должен
заменять рабочие секреты. Минимальные настройки подключения:

```dotenv
ENGINE=django.db.backends.postgresql
DB_HOST=host.docker.internal
DB_PORT=5432
DB_NAME=buyesai
DB_USER=buyesai
DB_PASSWORD=your-existing-database-password
```

`host.docker.internal` указывает на сервер, где запущен Docker; для Linux
в Compose добавлен `host-gateway`. `localhost` / `127.0.0.1` внутри контейнера
означает сам контейнер и для PostgreSQL на хосте не подходит.
Если PostgreSQL находится на другой машине, указать её DNS-имя или IP в `DB_HOST`.

Дополнительно указать:

- `DJANGO_SECRET_KEY`: секрет Django; при переносе рабочего сервиса сохранить
  действующий ключ, чтобы существующие сессии и подписи оставались валидными.
- `DJANGO_ALLOWED_HOSTS`: домены сайта без схемы и порта.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: адреса с протоколом и, при необходимости, портом.
- `CRM_PUBLIC_BASE_URL`: публичный адрес CRM для ссылок на документы.
- `DB_SSLMODE`: режим TLS PostgreSQL, по умолчанию `prefer`; для удалённой БД
  использовать режим, соответствующий конфигурации сервера и сертификатам.
- `DB_CONNECT_TIMEOUT`: таймаут одной попытки подключения, по умолчанию 5 секунд.
- `DB_WAIT_TIMEOUT_SECONDS`: время повторных попыток перед миграциями,
  по умолчанию 60 секунд (текущая попытка может дополнительно занять `DB_CONNECT_TIMEOUT`).

Новый секрет можно сгенерировать локально:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Compose задаёт `ENGINE=django.db.backends.postgresql`, `STATIC_ROOT=/app/staticfiles`,
`MEDIA_ROOT=/app/media` внутри контейнеров. Старые абсолютные пути с хоста
для статики и загрузок использовать не нужно.

Для отдельного файла окружения использовать оба параметра, например:

```bash
APP_ENV_FILE=.env.production docker compose --env-file .env.production up -d --build
```

`--env-file` задаёт значения для подстановок Compose, `APP_ENV_FILE` — файл
переменных, передаваемый приложению. Без них в обоих случаях используется `.env`.
Секреты, локальные базы, `media` и виртуальное окружение исключены из контекста сборки.

## Доступ к PostgreSQL на сервере

Использовать существующую базу и роль либо создать их на сервере заранее.
Роль приложения должна иметь права на миграции в своей базе и схеме.
В настройках PostgreSQL:

1. `listen_addresses` должен включать адрес хоста, доступный контейнерам.
   Прослушивания только `127.0.0.1` недостаточно при bridge-сети Docker на Linux.
2. В `pg_hba.conf` разрешить подключение пользователя приложения к его базе
   из подсети Docker с нужным методом аутентификации, например:

   ```text
   host buyesai buyesai <docker-subnet> scram-sha-256
   ```

3. Разрешить такой трафик в firewall. После правки `listen_addresses`
   перезапустить PostgreSQL, после правки только `pg_hba.conf` перечитать настройки.

Подсеть сети проекта можно узнать после создания контейнеров:

```bash
docker network inspect buyesai_default --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

Подставить фактическую подсеть вместо `<docker-subnet>`. Доступ к порту БД
нужен из сети контейнеров, публиковать его в интернет для этой схемы не требуется.

## Первый запуск

Сделать резервную копию существующей PostgreSQL перед применением миграций.
Если переносятся файлы с прежней установки, сначала загрузить их в том
по инструкции следующего раздела.

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps -a
docker compose logs setup web nginx
docker compose exec web python manage.py createsuperuser
```

Сайт: <http://localhost:8080>, CRM: <http://localhost:8080/crm/>.
Создание суперпользователя нужно только для новой базы.
`setup` должен завершиться с кодом `0`; это нормальное состояние разового сервиса.
При недоступной БД он завершится с ошибкой и приложение не стартует:
проверить `DB_HOST`, порт, права в `pg_hba.conf` и `docker compose logs setup`.
После исправления повторить `docker compose up -d`.

Для почты заполнить `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD`, затем:

```bash
docker compose --profile mail up -d
docker compose logs -f imap
```

Интервалы, лимиты и таймауты фоновых команд настраиваются теми же переменными,
что перечислены в [systemd_workers.md](systemd_workers.md), через `.env`.
Если в старой установке отдельно запускались `send_task_deadline_reminders` или
`send_lead_assignment_notifications`, их расписание нужно сохранить, заменив
команду на `docker compose exec -T web python manage.py <имя команды>`.

## Перенос файлов и фоновых процессов

Сохранить действующий `INTEGRATIONS_SECRET_KEY`: без него зашифрованные секреты
интеграций из существующей базы не расшифруются.
Остановить запись в старый сервис и сделать резервную копию каталога `media`.
Загрузить файлы в том Docker до запуска приложения:

```bash
docker compose build web
tar -C media -cf - . | docker compose run --rm --no-deps -T web tar --no-same-owner -xf - -C /app/media
```

При переходе с systemd отключить прежние poller-сервисы перед запуском контейнеров:

```bash
sudo systemctl disable --now buyesai-process-communications-outbox.service buyesai-fetch-imap-inbox.service buyesai-process-novofon-webhook-queue.service
docker compose up -d
```

## Обновление и обслуживание

Перед обновлением сделать резервную копию PostgreSQL на сервере. На время
миграций остановить приложение и обработчики, затем пересобрать образ и запустить:

```bash
docker compose --profile mail stop nginx web outbox novofon imap
docker compose up -d --build
```

Если почтовый профиль используется, добавить `--profile mail` и во вторую команду.

```bash
docker compose logs -f --tail=100 web outbox novofon
docker compose exec web python manage.py check
docker compose run --rm --no-deps -T web tar -cf - -C /app/media . > media-backup.tar
docker compose down
```

`down` сохраняет тома с файлами. `down -v` удаляет эти тома. PostgreSQL находится
вне Docker, её данные этими командами не затрагиваются.

## Публичный сервер и HTTPS

Для нескольких приложений используется общий серверный Nginx на портах 80/443.
Он завершает TLS и направляет `buyes.pro` на `127.0.0.1:8080`; внутренний Nginx
отдаёт файлы и проксирует Django. Публикация Docker-порта ограничена `127.0.0.1`
в `compose.yaml`, переменная `HTTP_BIND_ADDRESS` больше не используется.

Готовый конфиг, параметры `.env` и команды установки сертификата находятся в
[deploy/nginx/README.md](../deploy/nginx/README.md).

Серверный Nginx перезаписывает заголовки протокола и клиентского IP; внутренний
сохраняет их при передаче в Django. Оба перехода используют keepalive.
После настройки сертификата включить `DJANGO_TRUST_PROXY_HEADERS=True`,
`DJANGO_SESSION_COOKIE_SECURE=True` и `DJANGO_CSRF_COOKIE_SECURE=True`, а
`DJANGO_CSRF_TRUSTED_ORIGINS` / `CRM_PUBLIC_BASE_URL` настроить на `https://buyes.pro`.

Nginx отдаёт файлы `/media/` по прямым ссылкам, включая загруженные документы.
Для документов, требующих авторизации, следует использовать защищённую выдачу
через приложение вместо публичного location.

Порядок старта основан на [условиях зависимостей Compose](https://docs.docker.com/compose/how-tos/startup-order/).
