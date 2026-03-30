from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0075_settlementdocument_realization_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="settlementdocument",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("invoice", "Счет"),
                    ("realization", "Акт / накладная"),
                    ("supplier_receipt", "Поступление от поставщика"),
                    ("incoming_payment", "Оплата входящая"),
                    ("outgoing_payment", "Оплата исходящая"),
                    ("debt_adjustment", "Корректировка долга"),
                    ("refund", "Возврат"),
                    ("advance", "Аванс"),
                    ("advance_offset", "Зачет аванса"),
                ],
                max_length=32,
                verbose_name="Тип документа",
            ),
        ),
    ]
