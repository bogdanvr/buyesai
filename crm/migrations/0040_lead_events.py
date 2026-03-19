from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0039_alter_contact_telegram_alter_contactrole_created_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="lead",
            name="events",
            field=models.TextField(blank=True, default="", verbose_name="События"),
        ),
    ]
