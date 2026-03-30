import crm.models.settlement
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0073_settlement_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="settlementdocument",
            name="file",
            field=models.FileField(
                blank=True,
                max_length=500,
                null=True,
                upload_to=crm.models.settlement.settlement_document_upload_to,
                verbose_name="Файл",
            ),
        ),
        migrations.AddField(
            model_name="settlementdocument",
            name="original_name",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Название файла"),
        ),
    ]
