from django.db import migrations
def seed(apps,schema_editor):
 P=apps.get_model("persistence","SystemPermissionModel")
 for c,n in [("kpi.read","View KPI"),("kpi.manage","Manage KPI")]:P.objects.get_or_create(code=c,defaults={"name":n,"description":n})
class Migration(migrations.Migration):
 dependencies=[("persistence","0024_seed_payable_manage_permission")]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
