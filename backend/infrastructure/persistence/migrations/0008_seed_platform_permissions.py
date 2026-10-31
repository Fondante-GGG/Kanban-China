from django.db import migrations


PERMISSIONS = [
    ("hr.employee.read", "Read employees"), ("hr.employee.create", "Create employees"),
    ("hr.employee.edit", "Edit employees"), ("hr.employee.submit", "Submit hire"),
    ("hr.employee.approve", "Approve employee lifecycle"), ("hr.employee.terminate", "Submit termination"),
    ("hr.employee.onboarding", "Send onboarding invitation"), ("rbac.manage", "Manage system roles"),
    ("approval.read", "Read assigned approvals"), ("approval.act", "Act on assigned approvals"), ("audit.read", "Read audit log"),
]


def seed(apps, schema_editor):
    Permission = apps.get_model("persistence", "SystemPermissionModel")
    for code, name in PERMISSIONS:
        Permission.objects.get_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("persistence", "0007_onboarding_approval_assignment")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
