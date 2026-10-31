from django.db import migrations
def seed(apps, schema_editor):
    P=apps.get_model("persistence", "SystemPermissionModel")
    P.objects.get_or_create(code="finance.payable.manage", defaults={"name":"Manage payables","description":"Confirm supplier reconciliations"})
class Migration(migrations.Migration):
    dependencies=[("persistence","0023_supplier_reconciliation")]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
