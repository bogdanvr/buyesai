from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0002_seed_lead_statuses"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="client",
            options={
                "ordering": ("name",),
                "verbose_name": "Компания",
                "verbose_name_plural": "Компании",
            },
        ),
    ]
