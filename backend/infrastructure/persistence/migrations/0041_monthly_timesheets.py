from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("persistence", "0040_seed_warehouse_cost_read_permission")]
    operations = [
        migrations.CreateModel(
            name="MonthlyTimesheetModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField()), ("month", models.PositiveSmallIntegerField()),
                ("snapshot", models.JSONField(default=dict)),
                ("status", models.CharField(choices=[("confirmed", "Confirmed")], default="confirmed", max_length=20)),
                ("confirmed_at", models.DateTimeField(auto_now_add=True)),
                ("confirmed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="confirmed_timesheets", to="persistence.usermodel")),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="monthly_timesheets", to="persistence.employeemodel")),
            ],
            options={"db_table": "monthly_timesheets"},
        ),
        migrations.AddConstraint(model_name="monthlytimesheetmodel", constraint=models.UniqueConstraint(fields=("employee", "year", "month"), name="unique_employee_timesheet_period")),
    ]
