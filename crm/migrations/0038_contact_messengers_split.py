from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0037_contact_role_status_fk"),
    ]

    operations = [
        migrations.RenameField(
            model_name="contact",
            old_name="telegram_whatsapp",
            new_name="telegram",
        ),
        migrations.AddField(
            model_name="contact",
            name="whatsapp",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="WhatsApp"),
        ),
        migrations.AddField(
            model_name="contact",
            name="max_contact",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Max"),
        ),
    ]
