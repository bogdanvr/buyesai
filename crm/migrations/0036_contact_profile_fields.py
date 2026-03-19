from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0035_client_requisites_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="telegram_whatsapp",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Telegram / WhatsApp"),
        ),
        migrations.AddField(
            model_name="contact",
            name="role",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="Роль"),
        ),
        migrations.AddField(
            model_name="contact",
            name="contact_status",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="Статус контакта"),
        ),
        migrations.AddField(
            model_name="contact",
            name="person_note",
            field=models.TextField(blank=True, default="", verbose_name="Примечание"),
        ),
    ]
