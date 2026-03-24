from django.db import migrations, models


def copy_touch_result_relations_to_status_models(apps, schema_editor):
    LeadStatus = apps.get_model("crm", "LeadStatus")
    DealStage = apps.get_model("crm", "DealStage")
    TouchResult = apps.get_model("crm", "TouchResult")

    for touch_result in TouchResult.objects.all():
        for lead_status in touch_result.lead_statuses.all():
            lead_status.touch_results.add(touch_result)
        for deal_stage in touch_result.deal_stages.all():
            deal_stage.touch_results.add(touch_result)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0067_touchresult_lead_statuses_deal_stages"),
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
        migrations.RunPython(copy_touch_result_relations_to_status_models, noop_reverse),
        migrations.RemoveField(
            model_name="touchresult",
            name="deal_stages",
        ),
        migrations.RemoveField(
            model_name="touchresult",
            name="lead_statuses",
        ),
    ]
