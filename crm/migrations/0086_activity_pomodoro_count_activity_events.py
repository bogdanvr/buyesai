from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0085_trafficsource_alter_leadsource_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="events",
            field=models.TextField(blank=True, default="", verbose_name="История задачи"),
        ),
        migrations.AddField(
            model_name="activity",
            name="pomodoro_count",
            field=models.PositiveIntegerField(default=0, verbose_name="Количество pomodoro"),
        ),
    ]
