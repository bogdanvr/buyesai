from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0005_client_phone_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="address",
            field=models.CharField(blank=True, default="", max_length=512, verbose_name="Адрес"),
        ),
        migrations.AddField(
            model_name="client",
            name="industry",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Сфера деятельности"),
        ),
        migrations.AddField(
            model_name="client",
            name="okved",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="ОКВЭД"),
        ),
    ]
