from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0066_taskcategory_requires_follow_up_task_on_done_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="touchresult",
            name="deal_stages",
            field=models.ManyToManyField(
                blank=True,
                related_name="touch_results",
                to="crm.dealstage",
                verbose_name="Этапы сделок",
            ),
        ),
        migrations.AddField(
            model_name="touchresult",
            name="lead_statuses",
            field=models.ManyToManyField(
                blank=True,
                related_name="touch_results",
                to="crm.leadstatus",
                verbose_name="Статусы лидов",
            ),
        ),
    ]
