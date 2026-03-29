from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0070_alter_automationrule_create_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="checklist",
            field=models.JSONField(blank=True, default=list, verbose_name="Чек-лист"),
        ),
    ]
