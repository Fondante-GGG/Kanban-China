from django.db import migrations
def seed(apps,schema_editor):
 P=apps.get_model("persistence","SystemPermissionModel")
 for c,n in [("admin.license.read","View licenses"),("admin.license.manage","Manage licenses")]:P.objects.get_or_create(code=c,defaults={"name":n,"description":n})
class Migration(migrations.Migration):
 dependencies=[("persistence","0037_seed_transfer_permission")]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
