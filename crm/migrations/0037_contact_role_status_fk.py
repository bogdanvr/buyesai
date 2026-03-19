from django.db import migrations, models


def forward_fill_role_status(apps, schema_editor):
    Contact = apps.get_model("crm", "Contact")
    ContactRole = apps.get_model("crm", "ContactRole")
    ContactStatus = apps.get_model("crm", "ContactStatus")

    for contact in Contact.objects.all().iterator():
        updates = {}
        role_text = str(getattr(contact, "role_legacy", "") or "").strip()
        status_text = str(getattr(contact, "contact_status_legacy", "") or "").strip()
        if role_text:
            role_obj, _ = ContactRole.objects.get_or_create(name=role_text, defaults={"is_active": True})
            updates["role"] = role_obj
        if status_text:
            status_obj, _ = ContactStatus.objects.get_or_create(name=status_text, defaults={"is_active": True})
            updates["contact_status"] = status_obj
        if updates:
            for field_name, value in updates.items():
                setattr(contact, field_name, value)
            contact.save(update_fields=list(updates.keys()))


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0036_contact_profile_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContactRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=128, unique=True, verbose_name="Роль контакта")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активна")),
            ],
            options={
                "verbose_name": "Роль контакта",
                "verbose_name_plural": "Роли контактов",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="ContactStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=128, unique=True, verbose_name="Статус контакта")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
            ],
            options={
                "verbose_name": "Статус контакта",
                "verbose_name_plural": "Статусы контактов",
                "ordering": ("name",),
            },
        ),
        migrations.RenameField(
            model_name="contact",
            old_name="role",
            new_name="role_legacy",
        ),
        migrations.RenameField(
            model_name="contact",
            old_name="contact_status",
            new_name="contact_status_legacy",
        ),
        migrations.AddField(
            model_name="contact",
            name="role",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="contacts", to="crm.contactrole", verbose_name="Роль"),
        ),
        migrations.AddField(
            model_name="contact",
            name="contact_status",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="contacts", to="crm.contactstatus", verbose_name="Статус контакта"),
        ),
        migrations.RunPython(forward_fill_role_status, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="contact",
            name="role_legacy",
        ),
        migrations.RemoveField(
            model_name="contact",
            name="contact_status_legacy",
        ),
    ]
