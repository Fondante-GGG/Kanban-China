from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model("persistence", "SystemPermissionModel").objects.get_or_create(code="attendance.timesheet.confirm", defaults={"name": "Confirm monthly timesheets", "description": "Confirm an employee monthly attendance snapshot for payroll"})


class Migration(migrations.Migration):
    dependencies = [("persistence", "0041_monthly_timesheets")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
