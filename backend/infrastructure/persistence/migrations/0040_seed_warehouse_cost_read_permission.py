from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model("persistence", "SystemPermissionModel").objects.get_or_create(
        code="warehouse.cost.read",
        defaults={"name": "View warehouse cost", "description": "View weighted average inventory cost"},
    )


class Migration(migrations.Migration):
    dependencies = [("persistence", "0039_seed_warehouse_document_permissions")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
