from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0034_tasktype_auto_task_on_done_tasktype_auto_task_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="actual_address",
            field=models.CharField(blank=True, default="", max_length=512, verbose_name="Фактический адрес"),
        ),
        migrations.AddField(
            model_name="client",
            name="bank_details",
            field=models.TextField(blank=True, default="", verbose_name="Банковские реквизиты"),
        ),
        migrations.AddField(
            model_name="client",
            name="iban",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="ИИК / IBAN"),
        ),
        migrations.AddField(
            model_name="client",
            name="bik",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="БИК"),
        ),
        migrations.AddField(
            model_name="client",
            name="bank_name",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Банк"),
        ),
    ]
