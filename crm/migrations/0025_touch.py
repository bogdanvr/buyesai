from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0024_tasktype_activity_task_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Touch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("happened_at", models.DateTimeField(verbose_name="Дата и время")),
                ("direction", models.CharField(choices=[("incoming", "Входящее"), ("outgoing", "Исходящее")], max_length=16, verbose_name="Направление")),
                ("result", models.TextField(blank=True, default="", verbose_name="Результат")),
                ("summary", models.TextField(blank=True, default="", verbose_name="Краткое содержание")),
                ("next_step", models.TextField(blank=True, default="", verbose_name="Следующий шаг")),
                ("next_step_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата следующего шага")),
                ("channel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="touches", to="crm.communicationchannel", verbose_name="Тип канала")),
                ("deal", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="touches", to="crm.deal", verbose_name="Сделка")),
                ("lead", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="touches", to="crm.lead", verbose_name="Лид")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="crm_touches", to=settings.AUTH_USER_MODEL, verbose_name="Ответственный")),
            ],
            options={
                "verbose_name": "Касание",
                "verbose_name_plural": "Касания",
                "ordering": ("-happened_at", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="touch",
            index=models.Index(fields=["happened_at"], name="crm_touch_happene_f8ba5a_idx"),
        ),
        migrations.AddIndex(
            model_name="touch",
            index=models.Index(fields=["direction"], name="crm_touch_directi_d9f898_idx"),
        ),
        migrations.AddIndex(
            model_name="touch",
            index=models.Index(fields=["lead"], name="crm_touch_lead_id_37999e_idx"),
        ),
        migrations.AddIndex(
            model_name="touch",
            index=models.Index(fields=["deal"], name="crm_touch_deal_id_b18dfd_idx"),
        ),
    ]
