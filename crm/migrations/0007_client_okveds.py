from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0006_client_address_industry_okved"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="okveds",
            field=models.JSONField(blank=True, default=list, verbose_name="ОКВЭД (все виды)"),
        ),
    ]
