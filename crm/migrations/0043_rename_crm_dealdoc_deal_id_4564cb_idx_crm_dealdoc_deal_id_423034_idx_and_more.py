from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0042_dealdocument"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="dealdocument",
            new_name="crm_dealdoc_deal_id_423034_idx",
            old_name="crm_dealdoc_deal_id_4564cb_idx",
        ),
        migrations.AlterField(
            model_name="dealdocument",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Обновлено"),
        ),
    ]
