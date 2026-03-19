from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0038_contact_messengers_split"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="telegram",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Telegram"),
        ),
        migrations.AlterField(
            model_name="contactrole",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Создано"),
        ),
        migrations.AlterField(
            model_name="contactrole",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Обновлено"),
        ),
        migrations.AlterField(
            model_name="contactstatus",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Создано"),
        ),
        migrations.AlterField(
            model_name="contactstatus",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Обновлено"),
        ),
    ]
