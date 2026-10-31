from django.db import migrations


PERMISSIONS = [
    ("procurement.supplier.read", "View suppliers"),
    ("procurement.supplier.manage", "Manage suppliers"),
    ("procurement.sku.read", "View SKU catalogue"),
    ("procurement.sku.manage", "Manage SKU catalogue"),
    ("procurement.quote.manage", "Manage supplier quotes"),
]


def seed(apps, schema_editor):
    Permission = apps.get_model("persistence", "SystemPermissionModel")
    for code, name in PERMISSIONS:
        Permission.objects.get_or_create(code=code, defaults={"name": name, "description": name})


class Migration(migrations.Migration):
    dependencies = [("persistence", "0012_phase2_procurement_foundation")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
