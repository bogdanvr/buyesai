from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0028_touchresult_touch_result_option"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="touch",
            name="result",
        ),
    ]
