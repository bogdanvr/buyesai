from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0041_alter_activity_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DealDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменено")),
                ("file", models.FileField(upload_to="deal_documents/%Y/%m/%d/", verbose_name="Файл")),
                ("original_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Название файла")),
                ("deal", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="crm.deal", verbose_name="Сделка")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="crm_deal_documents", to=settings.AUTH_USER_MODEL, verbose_name="Загрузил")),
            ],
            options={
                "verbose_name": "Документ сделки",
                "verbose_name_plural": "Документы сделок",
                "ordering": ("-created_at", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="dealdocument",
            index=models.Index(fields=["deal"], name="crm_dealdoc_deal_id_4564cb_idx"),
        ),
    ]
