from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0069_communicationchannel_touch_results"),
    ]

    operations = [
        migrations.AlterField(
            model_name="automationrule",
            name="create_message",
            field=models.BooleanField(default=False, verbose_name="Создавать автоматическое сообщение"),
        ),
    ]
