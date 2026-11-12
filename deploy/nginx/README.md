# buyes.pro: серверный Nginx перед Docker

Схема: HTTPS → серверный Nginx → `127.0.0.1:8080` → Nginx в Docker → Django.
Сертификат и перенаправление HTTP на HTTPS находятся на серверном Nginx.
Внутренний Nginx отдаёт статику/загрузки и сохраняет переданный протокол.
Оба перехода используют HTTP/1.1 и keepalive.

Все команды ниже выполнять на сервере из каталога проекта после переноса
обновлённых `compose.yaml`, `deploy/docker` и `deploy/nginx`.

## 1. DNS и домен Django

A-запись `buyes.pro` должна указывать на IPv4 этого сервера. Если есть AAAA-запись,
она должна указывать на его рабочий IPv6. Порты 80/443 должны быть доступны извне.
Конфигурация рассчитана на `buyes.pro`; `www` автоматически не подключается.

В существующем `.env` обновить:

```dotenv
DJANGO_ALLOWED_HOSTS=buyes.pro,localhost,127.0.0.1
HTTP_PORT=8080
```

Остальные переменные, пароли и ключи сохранить. Docker-порт теперь всегда
публикуется только на `127.0.0.1`; прежняя переменная `HTTP_BIND_ADDRESS` не используется.

Пересобрать и заменить только внутренний Nginx, затем пересоздать приложение
с обновлённым списком доменов:

```bash
sudo docker compose build nginx
sudo docker compose up -d --no-deps nginx
sudo docker compose up -d --no-deps web
curl -I -H 'Host: buyes.pro' http://127.0.0.1:8080/
```

## 2. Серверный Nginx

Найти существующие конфиги этого домена:

```bash
sudo grep -RnsE 'server_name[^;]*buyes\.pro' /etc/nginx/sites-enabled /etc/nginx/conf.d
```

Если домен уже настроен, изменить его существующий конфиг: заменить старые
`root` / `alias` / `proxy_pass` для приложения на блок `location /` из
`buyes.pro.conf`, добавить `upstream buyesai_app` из этого файла в контекст `http`.
Существующие рабочие TLS-настройки сохранить; другие сайты не менять.
Дублирующихся `server_name buyes.pro` на одном listener быть не должно.

Если конфиг домена ещё не существует:

```bash
sudo cp -a /etc/nginx "/etc/nginx.backup-$(date +%Y%m%d-%H%M%S)"
sudo install -m 0644 deploy/nginx/buyes.pro.conf /etc/nginx/sites-available/buyes.pro.conf
sudo ln -s /etc/nginx/sites-available/buyes.pro.conf /etc/nginx/sites-enabled/buyes.pro.conf
sudo nginx -t && sudo systemctl reload nginx
curl -I --resolve buyes.pro:80:127.0.0.1 http://buyes.pro/
```

Этот файл сначала включает HTTP без ссылок на ещё не существующие сертификаты.
Серверный Nginx перезаписывает `X-Forwarded-Proto`, `X-Real-IP` и `X-Forwarded-For`;
внутренний доверяет им только при работе за этим локальным входом.

## 3. Сертификат HTTPS

Если валидный сертификат и автоматическое продление уже настроены, сохранить их
и перейти к следующему разделу. Иначе установить Certbot и выпустить сертификат:

```bash
sudo snap install --classic certbot
sudo /snap/bin/certbot --nginx --redirect -d buyes.pro
sudo nginx -t
sudo /snap/bin/certbot renew --dry-run
```

Если `snap` отсутствует, сначала установить `snapd` через `sudo apt install snapd`.
Certbot интерактивно запросит данные для регистрации и настроит HTTPS и редирект
в конфиге серверного Nginx. После этого не заменять этот файл исходным HTTP-шаблоном.
Проверить автоматическое продление:

```bash
sudo systemctl status snap.certbot.renew.timer --no-pager
```

Порядок выпуска и проверки соответствует [инструкции Ubuntu](https://ubuntu.com/server/docs/how-to/security/obtain-tls-certificates/).

## 4. HTTPS в Django

После успешного выпуска сертификата перенести параметры из `buyes.pro.env.example`
в существующий `.env` (это частичный пример, не полная замена `.env`):

```dotenv
DEBUG=False
DJANGO_ALLOWED_HOSTS=buyes.pro,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://buyes.pro
DJANGO_TRUST_PROXY_HEADERS=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
CRM_PUBLIC_BASE_URL=https://buyes.pro
HTTP_PORT=8080
```

Применить окружение к веб-приложению и обработчикам:

```bash
sudo docker compose up -d --no-deps web outbox novofon
```

Если IMAP используется, отдельно пересоздать его с профилем:

```bash
sudo docker compose --profile mail up -d --no-deps imap
```

`restart` не перечитывает `.env`, поэтому здесь используется `up -d`.

## 5. Проверка

```bash
curl -I http://buyes.pro/
curl -I https://buyes.pro/
sudo docker compose ps -a
sudo docker compose logs --tail=100 nginx web
```

HTTP должен перенаправлять на HTTPS, а HTTPS — отвечать успешно.
Проверить вход в `/crm/` или `/admin/` и отправку формы в браузере: без ошибки CSRF.
В ответе со свежим CSRF-cookie должен присутствовать атрибут `Secure`.

Для следующего приложения добавить отдельный доменный конфиг и upstream
на свободный локальный порт, например `127.0.0.1:8081`, сохранив общий Nginx на 80/443.
