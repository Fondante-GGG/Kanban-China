from django.db import migrations

def seed(apps, schema_editor):
    P = apps.get_model("persistence", "SystemPermissionModel")
    for code, name in [("procurement.order.read", "View purchase orders"), ("procurement.order.manage", "Manage purchase orders")]:
        P.objects.get_or_create(code=code, defaults={"name": name, "description": name})

class Migration(migrations.Migration):
    dependencies = [("persistence", "0014_purchase_orders")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
