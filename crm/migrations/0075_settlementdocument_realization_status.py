from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0074_settlementdocument_file_and_original_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="settlementdocument",
            name="realization_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("created", "Создан"),
                    ("sent_to_client", "Отправлен клиенту"),
                    ("signed", "Подписан"),
                ],
                default="",
                max_length=32,
                verbose_name="Статус акта",
            ),
        ),
    ]
