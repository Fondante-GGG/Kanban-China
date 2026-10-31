from django.db import migrations
def seed(apps, schema_editor):
    P=apps.get_model("persistence", "SystemPermissionModel")
    for code,name in [("finance.account.manage","Manage finance accounts"),("finance.payable.read","View payables"),("finance.payment.manage","Make payments")]: P.objects.get_or_create(code=code, defaults={"name":name,"description":name})
class Migration(migrations.Migration):
    dependencies=[("persistence","0021_kpi_admin_foundation")]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
