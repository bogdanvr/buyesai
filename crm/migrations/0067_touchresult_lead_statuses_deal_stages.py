from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0066_taskcategory_requires_follow_up_task_on_done_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dealstage",
            name="touch_results",
            field=models.ManyToManyField(
                blank=True,
                related_name="deal_stages",
                to="crm.touchresult",
                verbose_name="Результаты касаний",
            ),
        ),
        migrations.AddField(
            model_name="leadstatus",
            name="touch_results",
            field=models.ManyToManyField(
                blank=True,
                related_name="lead_statuses",
                to="crm.touchresult",
                verbose_name="Результаты касаний",
            ),
        ),
    ]
