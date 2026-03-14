from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0003_client_verbose_name_company"),
    ]

    operations = [
        migrations.AlterField(
            model_name="deal",
            name="client",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="deals",
                to="crm.client",
                verbose_name="Клиент",
            ),
        ),
    ]
