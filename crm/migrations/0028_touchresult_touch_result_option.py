from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0027_rename_crm_activit_status_f36e34_idx_crm_activit_status_2d8c1f_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TouchResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=128, unique=True, verbose_name="Результат касания")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
            ],
            options={
                "verbose_name": "Результат касания",
                "verbose_name_plural": "Результаты касаний",
                "ordering": ("name",),
            },
        ),
        migrations.AddField(
            model_name="touch",
            name="result_option",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="touches", to="crm.touchresult", verbose_name="Результат касания"),
        ),
    ]
