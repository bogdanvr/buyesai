from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0072_client_bank_accounts_and_registry_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="SettlementContract",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
                ("title", models.CharField(blank=True, default="", max_length=255, verbose_name="Название договора")),
                ("number", models.CharField(blank=True, default="", max_length=128, verbose_name="Номер договора")),
                ("currency", models.CharField(default="RUB", max_length=3, verbose_name="Валюта")),
                ("start_date", models.DateField(blank=True, null=True, verbose_name="Дата начала")),
                ("end_date", models.DateField(blank=True, null=True, verbose_name="Дата окончания")),
                ("note", models.TextField(blank=True, default="", verbose_name="Комментарий")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="settlement_contracts", to="crm.client", verbose_name="Компания")),
            ],
            options={
                "verbose_name": "Договор взаиморасчетов",
                "verbose_name_plural": "Договоры взаиморасчетов",
                "ordering": ("-created_at", "-id"),
            },
        ),
        migrations.CreateModel(
            name="SettlementDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
                ("document_type", models.CharField(choices=[("invoice", "Счет"), ("realization", "Реализация / акт / накладная"), ("supplier_receipt", "Поступление от поставщика"), ("incoming_payment", "Оплата входящая"), ("outgoing_payment", "Оплата исходящая"), ("debt_adjustment", "Корректировка долга"), ("refund", "Возврат"), ("advance", "Аванс"), ("advance_offset", "Зачет аванса")], max_length=32, verbose_name="Тип документа")),
                ("flow_direction", models.CharField(blank=True, choices=[("incoming", "Входящий"), ("outgoing", "Исходящий")], default="", max_length=16, verbose_name="Направление потока")),
                ("title", models.CharField(blank=True, default="", max_length=255, verbose_name="Название")),
                ("number", models.CharField(blank=True, default="", max_length=128, verbose_name="Номер документа")),
                ("document_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="Дата документа")),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="Срок оплаты")),
                ("currency", models.CharField(default="RUB", max_length=3, verbose_name="Валюта")),
                ("amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14, verbose_name="Сумма")),
                ("open_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14, verbose_name="Остаток")),
                ("note", models.TextField(blank=True, default="", verbose_name="Комментарий")),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="settlement_documents", to="crm.client", verbose_name="Компания")),
                ("contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="documents", to="crm.settlementcontract", verbose_name="Договор")),
            ],
            options={
                "verbose_name": "Документ взаиморасчетов",
                "verbose_name_plural": "Документы взаиморасчетов",
                "ordering": ("-document_date", "-id"),
            },
        ),
        migrations.CreateModel(
            name="SettlementAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
                ("amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14, verbose_name="Сумма распределения")),
                ("allocated_at", models.DateField(default=django.utils.timezone.localdate, verbose_name="Дата распределения")),
                ("note", models.TextField(blank=True, default="", verbose_name="Комментарий")),
                ("source_document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_allocations", to="crm.settlementdocument", verbose_name="Источник закрытия")),
                ("target_document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_allocations", to="crm.settlementdocument", verbose_name="Закрываемый документ")),
            ],
            options={
                "verbose_name": "Распределение взаиморасчетов",
                "verbose_name_plural": "Распределения взаиморасчетов",
                "ordering": ("-allocated_at", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="settlementcontract",
            index=models.Index(fields=["client", "is_active"], name="crm_settlem_client__bdf24c_idx"),
        ),
        migrations.AddIndex(
            model_name="settlementdocument",
            index=models.Index(fields=["client", "document_type"], name="crm_settlem_client__57d59c_idx"),
        ),
        migrations.AddIndex(
            model_name="settlementdocument",
            index=models.Index(fields=["client", "contract"], name="crm_settlem_client__237403_idx"),
        ),
        migrations.AddIndex(
            model_name="settlementdocument",
            index=models.Index(fields=["due_date"], name="crm_settlem_due_dat_5c0d70_idx"),
        ),
        migrations.AddIndex(
            model_name="settlementallocation",
            index=models.Index(fields=["source_document"], name="crm_settlem_source__14f60d_idx"),
        ),
        migrations.AddIndex(
            model_name="settlementallocation",
            index=models.Index(fields=["target_document"], name="crm_settlem_target__00f639_idx"),
        ),
    ]
