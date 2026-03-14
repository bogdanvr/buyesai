from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0007_client_okveds"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="deadline_reminder_sent_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Напоминание о дедлайне отправлено",
            ),
        ),
    ]
