from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model("persistence", "SystemPermissionModel").objects.get_or_create(code="admin.request.manage", defaults={"name":"Manage administrative requests", "description":"Approve stationery and other administrative requests"})


class Migration(migrations.Migration):
    dependencies = [("persistence", "0042_seed_timesheet_confirm_permission")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
