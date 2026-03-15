from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_formsubmission_utm_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebsiteSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_id", models.CharField(db_index=True, max_length=64, unique=True, verbose_name="Внутренний session_id")),
                ("utm_source", models.CharField(blank=True, default="", max_length=255, verbose_name="utm_source")),
                ("utm_medium", models.CharField(blank=True, default="", max_length=255, verbose_name="utm_medium")),
                ("utm_campaign", models.CharField(blank=True, default="", max_length=255, verbose_name="utm_campaign")),
                ("utm_content", models.CharField(blank=True, default="", max_length=255, verbose_name="utm_content")),
                ("utm_term", models.CharField(blank=True, default="", max_length=255, verbose_name="utm_term")),
                ("yclid", models.CharField(blank=True, default="", max_length=255, verbose_name="yclid")),
                ("referer", models.TextField(blank=True, default="", verbose_name="Referer")),
                ("landing_url", models.TextField(blank=True, default="", verbose_name="Landing URL")),
                ("client_id", models.CharField(blank=True, default="", max_length=255, verbose_name="Client ID")),
                ("first_visit_at", models.DateTimeField(auto_now_add=True, verbose_name="Первый визит")),
                ("first_message_at", models.DateTimeField(blank=True, null=True, verbose_name="Первое сообщение")),
                ("first_message", models.TextField(blank=True, default="", verbose_name="Первое сообщение")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
            ],
            options={
                "verbose_name": "Веб-сессия",
                "verbose_name_plural": "Веб-сессии",
                "ordering": ("-first_visit_at",),
            },
        ),
        migrations.CreateModel(
            name="WebsiteSessionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(db_index=True, max_length=64, verbose_name="Событие")),
                ("page_url", models.TextField(blank=True, default="", verbose_name="URL страницы")),
                ("payload", models.JSONField(blank=True, default=dict, verbose_name="Payload")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="main.websitesession",
                        verbose_name="Веб-сессия",
                    ),
                ),
            ],
            options={
                "verbose_name": "Событие веб-сессии",
                "verbose_name_plural": "События веб-сессий",
                "ordering": ("created_at", "id"),
            },
        ),
    ]
