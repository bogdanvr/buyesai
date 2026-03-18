from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0023_lead_assignment_notification_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=128, unique=True, verbose_name="Тип задачи")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
            ],
            options={
                "verbose_name": "Тип задачи",
                "verbose_name_plural": "Типы задач",
                "ordering": ("name",),
            },
        ),
        migrations.AddField(
            model_name="activity",
            name="priority",
            field=models.CharField(
                choices=[("low", "Низкий"), ("medium", "Средний"), ("high", "Высокий")],
                default="medium",
                max_length=16,
                verbose_name="Приоритет",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="related_touch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="related_tasks",
                to="crm.activity",
                verbose_name="Связанное касание",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="status",
            field=models.CharField(
                choices=[
                    ("todo", "К выполнению"),
                    ("in_progress", "В работе"),
                    ("done", "Выполнено"),
                    ("canceled", "Отменено"),
                ],
                default="todo",
                max_length=16,
                verbose_name="Статус задачи",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="task_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="activities",
                to="crm.tasktype",
                verbose_name="Тип задачи",
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE crm_activity SET status = 'done' WHERE type = 'task' AND is_done = 1",
            reverse_sql="UPDATE crm_activity SET is_done = 1 WHERE type = 'task' AND status = 'done'",
        ),
        migrations.RunSQL(
            sql="""UPDATE crm_activity SET status = 'in_progress'
                   WHERE type = 'task' AND (status IS NULL OR status = '') AND is_done = 0""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AddIndex(
            model_name="activity",
            index=models.Index(fields=["status"], name="crm_activit_status_f36e34_idx"),
        ),
    ]
