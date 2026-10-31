from django.db import migrations


def seed(apps, schema_editor):
    permission = apps.get_model("persistence", "SystemPermissionModel")
    for code, name, description in (
        ("warehouse.receipt.read", "View purchase receipts", "View warehouse receipt documents"),
        ("warehouse.receipt.manage", "Manage purchase receipts", "Create warehouse receipt documents"),
        ("warehouse.transfer.read", "View stock transfers", "View inter-warehouse transfer documents"),
        ("warehouse.transfer.manage", "Manage stock transfers", "Create inter-warehouse transfer documents"),
        ("warehouse.count.read", "View stock counts", "View stock-count documents"),
        ("warehouse.count.manage", "Manage stock counts", "Create stock-count documents"),
    ):
        permission.objects.get_or_create(code=code, defaults={"name": name, "description": description})


class Migration(migrations.Migration):
    dependencies = [("persistence", "0038_seed_license_permissions")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
