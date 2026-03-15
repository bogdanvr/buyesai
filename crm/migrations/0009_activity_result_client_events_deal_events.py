from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0008_activity_deadline_reminder_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="result",
            field=models.TextField(blank=True, default="", verbose_name="Результат"),
        ),
        migrations.AddField(
            model_name="client",
            name="events",
            field=models.TextField(blank=True, default="", verbose_name="События"),
        ),
        migrations.AddField(
            model_name="deal",
            name="events",
            field=models.TextField(blank=True, default="", verbose_name="События"),
        ),
    ]
