from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_profiles_for_existing_users(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserIntegrationProfile = apps.get_model("integrations", "UserIntegrationProfile")
    for user in User.objects.all().iterator():
        UserIntegrationProfile.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserIntegrationProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone", models.CharField(blank=True, default="", max_length=64, verbose_name="Телефон")),
                (
                    "telegram_chat_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Личный chat_id, куда бот будет отправлять уведомления",
                        max_length=64,
                        verbose_name="Telegram chat ID",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="integration_profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Интеграционный профиль пользователя",
                "verbose_name_plural": "Интеграционные профили пользователей",
            },
        ),
        migrations.RunPython(create_profiles_for_existing_users, migrations.RunPython.noop),
    ]
