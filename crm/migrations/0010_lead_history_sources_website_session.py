from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0008_websitesession_websitesessionevent"),
        ("crm", "0009_activity_result_client_events_deal_events"),
    ]

    operations = [
        migrations.AddField(
            model_name="lead",
            name="history",
            field=models.JSONField(blank=True, default=list, verbose_name="История"),
        ),
        migrations.AddField(
            model_name="lead",
            name="sources",
            field=models.ManyToManyField(blank=True, related_name="tracked_leads", to="crm.leadsource", verbose_name="Источники"),
        ),
        migrations.AddField(
            model_name="lead",
            name="website_session",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="leads",
                to="main.websitesession",
                verbose_name="Веб-сессия",
            ),
        ),
    ]
