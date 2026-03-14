from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0004_deal_client_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="email",
            field=models.EmailField(blank=True, default="", max_length=254, verbose_name="Email"),
        ),
        migrations.AddField(
            model_name="client",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="Телефон"),
        ),
    ]
