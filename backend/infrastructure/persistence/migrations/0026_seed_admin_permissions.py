from django.db import migrations
def seed(apps,schema_editor):
 P=apps.get_model("persistence","SystemPermissionModel")
 for c,n in [("admin.asset.read","View assets"),("admin.asset.manage","Manage assets"),("admin.notice.read","View notices"),("admin.notice.manage","Manage notices")]:P.objects.get_or_create(code=c,defaults={"name":n,"description":n})
class Migration(migrations.Migration):
 dependencies=[("persistence","0025_seed_kpi_permissions")]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
