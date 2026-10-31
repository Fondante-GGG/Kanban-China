from django.db import migrations
def seed(apps,schema_editor):
 P=apps.get_model("persistence","SystemPermissionModel")
 for c,n in [("finance.salary.read","View salaries"),("finance.salary.manage","Manage salaries")]:P.objects.get_or_create(code=c,defaults={"name":n,"description":n})
class Migration(migrations.Migration):
 dependencies=[("persistence","0027_salaries")]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
