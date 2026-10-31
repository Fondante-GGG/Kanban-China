from django.db import migrations
def seed(apps, schema_editor):
    P = apps.get_model("persistence", "SystemPermissionModel")
    P.objects.get_or_create(code="warehouse.receipt.post", defaults={"name": "Post purchase receipts", "description": "Post warehouse purchase receipts"})
class Migration(migrations.Migration):
    dependencies = [("persistence", "0017_stock_receipts_ledger")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
