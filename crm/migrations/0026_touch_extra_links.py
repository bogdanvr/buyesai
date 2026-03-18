from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0025_touch"),
    ]

    operations = [
        migrations.AddField(
            model_name="touch",
            name="client",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="touches", to="crm.client", verbose_name="Компания"),
        ),
        migrations.AddField(
            model_name="touch",
            name="contact",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="touches", to="crm.contact", verbose_name="Контакт"),
        ),
        migrations.AddField(
            model_name="touch",
            name="task",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="touches", to="crm.activity", verbose_name="Задача"),
        ),
        migrations.AddIndex(
            model_name="touch",
            index=models.Index(fields=["client"], name="crm_touch_client__1d8153_idx"),
        ),
        migrations.AddIndex(
            model_name="touch",
            index=models.Index(fields=["contact"], name="crm_touch_contact_e5e3b0_idx"),
        ),
        migrations.AddIndex(
            model_name="touch",
            index=models.Index(fields=["task"], name="crm_touch_task_id_85d578_idx"),
        ),
    ]
