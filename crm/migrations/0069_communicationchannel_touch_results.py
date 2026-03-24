from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0068_move_touchresult_links_to_status_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="communicationchannel",
            name="touch_results",
            field=models.ManyToManyField(
                blank=True,
                related_name="communication_channels",
                to="crm.touchresult",
                verbose_name="Допустимые результаты касаний",
            ),
        ),
    ]
