from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0071_activity_checklist"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="correspondent_account",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="Корреспондентский счет"),
        ),
        migrations.AddField(
            model_name="client",
            name="kpp",
            field=models.CharField(blank=True, default="", max_length=9, verbose_name="КПП"),
        ),
        migrations.AddField(
            model_name="client",
            name="ogrn",
            field=models.CharField(blank=True, default="", max_length=15, verbose_name="ОГРН"),
        ),
        migrations.AddField(
            model_name="client",
            name="settlement_account",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="Расчетный счет"),
        ),
    ]
